using System;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using Ultron.Net.Audio;
using Ultron.Shared.Config;
using Ultron.Shared.Services;
using Ultron.Net.Tools;

namespace Ultron.Net.Services
{
    public class Orchestrator : IDisposable
    {
        private readonly UltronConfig _config;
        private readonly GroqService _groq;
        private readonly TtsService _tts;
        private readonly WasapiListener _listener;

        private bool _isSessionActive = false;
        private DateTime _sessionExpiry = DateTime.MinValue;

        public event Action<string, string>? OnSubtitlesChanged;
        public event Action<string>? OnStateChanged;

        public Orchestrator(UltronConfig config)
        {
            _config = config;
            _groq = new GroqService(config);
            _tts = new TtsService(config);
            _listener = new WasapiListener(config, _tts);

            _listener.OnSpeechCaptured += (wavBytes) =>
            {
                Task.Run(async () => await ProcessSpeechAsync(wavBytes));
            };
        }

        public void Start()
        {
            _listener.Start();
            OnStateChanged?.Invoke("LISTENING");
            _tts.Speak("Ultron systems online and operational, sir.");
        }

        public void Stop()
        {
            _listener.Stop();
            _tts.Stop();
        }

        private async Task ProcessSpeechAsync(byte[] wavBytes)
        {
            OnStateChanged?.Invoke("PROCESSING");

            string transcript = await _groq.TranscribeAudioAsync(wavBytes);
            if (string.IsNullOrWhiteSpace(transcript))
            {
                OnStateChanged?.Invoke("LISTENING");
                return;
            }

            string clean = transcript.Trim();
            string lower = clean.ToLower();

            // Discard common Whisper silence hallucinations
            if (lower == "thank you." || lower == "thank you" || lower == "thanks." || lower == "you" || lower == "tron" || lower.Length <= 2)
            {
                OnStateChanged?.Invoke("LISTENING");
                return;
            }

            Console.WriteLine($"[Heard] '{clean}'");

            // Wake word / Session checking
            bool hasWakeWord = lower.Contains(_config.WakeWord);
            bool isSessionValid = _isSessionActive && DateTime.UtcNow < _sessionExpiry;

            if (!hasWakeWord && !isSessionValid)
            {
                OnStateChanged?.Invoke("LISTENING");
                return;
            }

            // Strip wake word
            string command = Regex.Replace(clean, $@"\b{_config.WakeWord}\b", "", RegexOptions.IgnoreCase).Trim();
            if (string.IsNullOrEmpty(command))
            {
                _isSessionActive = true;
                _sessionExpiry = DateTime.UtcNow.AddSeconds(6);
                OnSubtitlesChanged?.Invoke(clean, "At your service, sir.");
                _tts.Speak("At your service, sir.");
                OnStateChanged?.Invoke("LISTENING");
                return;
            }

            OnSubtitlesChanged?.Invoke(clean, "Executing...");

            // Check Instant System Vitals Shortcut
            if (lower.Contains("battery") || lower.Contains("system vitals") || lower.Contains("vitals"))
            {
                string vitals = WindowsAutomator.GetSystemVitals();
                OnSubtitlesChanged?.Invoke(clean, vitals);
                _tts.Speak(vitals);
                ExtendSession();
                OnStateChanged?.Invoke("LISTENING");
                return;
            }

            // Neural Action Classification (Groq LPU LLM)
            var action = await _groq.ClassifyActionAsync(command);
            string result = "";

            switch (action.Action?.ToLower())
            {
                case "type":
                    result = WindowsAutomator.TypeInActiveEditor(action.Text ?? command);
                    break;

                case "replace_in_app":
                    result = WindowsAutomator.ReplaceInActiveEditor(action.Find ?? "", action.Replace ?? "");
                    break;

                case "clear_in_app":
                    result = WindowsAutomator.ClearActiveEditor();
                    break;

                case "delete_in_app":
                    if (action.Scope?.Contains("line") == true)
                        result = WindowsAutomator.DeleteLine();
                    else
                        result = WindowsAutomator.DeleteLastWord();
                    break;

                case "undo":
                    result = WindowsAutomator.Undo();
                    break;

                case "redo":
                    result = WindowsAutomator.Redo();
                    break;

                case "save":
                    result = WindowsAutomator.SaveDocument();
                    break;

                case "open_app":
                    result = WindowsAutomator.LaunchApplication(action.App ?? command);
                    break;

                case "open_folder":
                    result = WindowsAutomator.OpenFolderOrDrive(action.Folder ?? command);
                    break;

                case "modify_file":
                    result = WindowsAutomator.FindAndModifyFile(action.File ?? "notes.txt", action.Instruction ?? command);
                    break;

                case "delete_file":
                    result = WindowsAutomator.DeleteFileOnDisk(action.File ?? "");
                    break;

                case "chat":
                default:
                    result = await _groq.GenerateChatResponseAsync(action.Query ?? command);
                    break;
            }

            if (!string.IsNullOrWhiteSpace(result))
            {
                OnSubtitlesChanged?.Invoke(clean, result);
                _tts.Speak(result);
            }

            ExtendSession();
            OnStateChanged?.Invoke("LISTENING");
        }

        private void ExtendSession()
        {
            _isSessionActive = true;
            _sessionExpiry = DateTime.UtcNow.AddSeconds(7);
        }

        public void Dispose()
        {
            _listener?.Dispose();
            _tts?.Dispose();
        }
    }
}
