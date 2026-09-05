using System;
using System.Speech.Synthesis;
using Ultron.Shared.Config;

namespace Ultron.Net.Services
{
    public class TtsService : IDisposable
    {
        private readonly SpeechSynthesizer _synthesizer;
        private readonly UltronConfig _config;
        private volatile bool _isSpeaking;

        public bool IsSpeaking => _isSpeaking;

        public event Action? OnSpeechStarted;
        public event Action? OnSpeechCompleted;

        public TtsService(UltronConfig config)
        {
            _config = config;
            _synthesizer = new SpeechSynthesizer();

            // Configure voice
            try
            {
                foreach (var installedVoice in _synthesizer.GetInstalledVoices())
                {
                    if (installedVoice.Enabled && installedVoice.VoiceInfo.Name.Contains("David"))
                    {
                        _synthesizer.SelectVoice(installedVoice.VoiceInfo.Name);
                        break;
                    }
                }
            }
            catch { }

            _synthesizer.Rate = _config.TtsRate;
            _synthesizer.Volume = 100;

            _synthesizer.SpeakStarted += (s, e) =>
            {
                _isSpeaking = true;
                OnSpeechStarted?.Invoke();
            };

            _synthesizer.SpeakCompleted += (s, e) =>
            {
                _isSpeaking = false;
                OnSpeechCompleted?.Invoke();
            };
        }

        public void Speak(string text, bool async = true)
        {
            if (string.IsNullOrWhiteSpace(text))
                return;

            try
            {
                Stop();
                if (async)
                {
                    _synthesizer.SpeakAsync(text);
                }
                else
                {
                    _synthesizer.Speak(text);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[TTS] Error speaking: {ex.Message}");
                _isSpeaking = false;
            }
        }

        public void Stop()
        {
            try
            {
                _synthesizer.SpeakAsyncCancelAll();
            }
            catch { }
            finally
            {
                _isSpeaking = false;
            }
        }

        public void Dispose()
        {
            _synthesizer?.Dispose();
        }
    }
}
