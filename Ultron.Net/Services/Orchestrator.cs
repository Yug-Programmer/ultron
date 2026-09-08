using System;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using Ultron.Net.Audio;
using Ultron.Shared.Config;
using Ultron.Shared.Memory;
using Ultron.Shared.Services;
using Ultron.Net.Tools;

namespace Ultron.Net.Services
{
    public class Orchestrator : IDisposable
    {
        private readonly UltronConfig _config;
        private readonly GroqService _groq;
        private readonly NluEngine _nlu;
        private readonly TtsService _tts;
        private readonly WasapiListener _listener;
        private readonly ScreenWatcher _screenWatcher;
        private readonly MemoryService _memory;

        private bool _isSessionActive = false;
        private DateTime _sessionExpiry = DateTime.MinValue;

        public ScreenWatcher ScreenWatcher => _screenWatcher;
        public MemoryService Memory => _memory;

        public event Action<string, string>? OnSubtitlesChanged;
        public event Action<string>? OnStateChanged;

        public Orchestrator(UltronConfig config)
        {
            _config = config;
            _memory = MemoryService.Instance;
            _screenWatcher = new ScreenWatcher(_memory);
            _groq = new GroqService(config);
            _nlu = new NluEngine(config);
            _tts = new TtsService(config);
            _listener = new WasapiListener(config, _tts);

            _screenWatcher.OnWindowChanged += (proc, title) =>
            {
                _nlu.Context.LastActiveApp = proc;
            };

            _listener.OnSpeechCaptured += (wavBytes) =>
            {
                Task.Run(async () => await ProcessSpeechAsync(wavBytes));
            };
        }

        public void Start()
        {
            _screenWatcher.Start();
            _listener.Start();
            OnStateChanged?.Invoke("LISTENING");
            _tts.Speak("Ultron systems online and operational, sir.");
        }

        public void Stop()
        {
            _screenWatcher.Stop();
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

            // Deep Multilingual Neural NLU & Contextual Engine
            var action = await _nlu.UnderstandAsync(command);
            string result = "";

            switch (action.Action?.ToLower())
            {
                case "vitals":
                    result = WindowsAutomator.GetSystemVitals();
                    break;
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
                    _ = Task.Run(async () => await _memory.LogFileActivityAsync(action.File ?? "notes.txt", "modify"));
                    break;

                case "delete_file":
                    result = WindowsAutomator.DeleteFileOnDisk(action.File ?? "");
                    _ = Task.Run(async () => await _memory.LogFileActivityAsync(action.File ?? "", "delete"));
                    break;

                case "recall_activity":
                    result = await _memory.FormatTimelineSummaryAsync(hours: 12);
                    break;

                case "remember_fact":
                    var factReply = await _nlu.Personalization.TryHandleExplicitMemoryCommandAsync("remember that " + (action.Text ?? command));
                    result = factReply ?? "Fact committed to permanent memory, sir.";
                    break;

                case "who_am_i":
                    var whoReply = await _nlu.Personalization.TryHandleExplicitMemoryCommandAsync("who am i");
                    result = whoReply ?? "I am Ultron, your personalized AI assistant.";
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
                _ = Task.Run(async () => await _memory.LogInteractionAsync(clean, action.Action ?? "chat", result, _nlu.Context.LastActiveApp));
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
            _screenWatcher?.Dispose();
            _listener?.Dispose();
            _tts?.Dispose();
        }
    }
}
