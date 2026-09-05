using System;
using Android.Content;
using Android.Speech.Tts;
using Java.Util;

namespace Ultron.Android.Services
{
    public class AndroidTts : Java.Lang.Object, TextToSpeech.IOnInitListener, IDisposable
    {
        private TextToSpeech? _tts;
        private bool _isReady = false;
        private volatile bool _isSpeaking = false;

        public bool IsSpeaking => _isSpeaking;

        public AndroidTts(Context context)
        {
            _tts = new TextToSpeech(context, this);
        }

        public void OnInit(OperationResult status)
        {
            if (status == OperationResult.Success && _tts != null)
            {
                _tts.SetLanguage(Locale.Us);
                _tts.SetSpeechRate(1.05f);
                _tts.SetPitch(0.95f);
                _isReady = true;
            }
        }

        public void Speak(string text)
        {
            if (!_isReady || _tts == null || string.IsNullOrWhiteSpace(text))
                return;

            _isSpeaking = true;
            _tts.Speak(text, QueueMode.Flush, null, "UltronUtteranceId");
        }

        public void Stop()
        {
            _tts?.Stop();
            _isSpeaking = false;
        }

        public new void Dispose()
        {
            Stop();
            _tts?.Shutdown();
            _tts?.Dispose();
            _tts = null;
            base.Dispose();
        }
    }
}
