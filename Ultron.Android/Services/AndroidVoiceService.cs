using System;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using Android.App;
using Android.Content;
using Android.Hardware.Camera2;
using Android.Media;
using Android.OS;
using Ultron.Shared.Config;
using Ultron.Shared.Services;

namespace Ultron.Android.Services
{
    [Service(ForegroundServiceType = global::Android.Content.PM.ForegroundService.TypeMicrophone)]
    public class AndroidVoiceService : Service
    {
        private const string ChannelId = "UltronVoiceChannel";
        private const int NotificationId = 1001;

        private AudioRecord? _audioRecord;
        private Thread? _recordingThread;
        private volatile bool _isRunning = false;

        private UltronConfig _config = new();
        private GroqService? _groq;
        private AndroidTts? _tts;

        private bool _isSpeaking = false;
        private DateTime? _silenceStart = null;
        private readonly List<byte> _audioBuffer = new();

        public override IBinder? OnBind(Intent? intent) => null;

        public override void OnCreate()
        {
            base.OnCreate();
            _config = UltronConfig.Load();
            _groq = new GroqService(_config);
            _tts = new AndroidTts(this);

            CreateNotificationChannel();
            var notification = BuildNotification("Ultron AI is listening...");
            StartForeground(NotificationId, notification);

            StartAudioRecording();
        }

        private void StartAudioRecording()
        {
            int sampleRate = 16000;
            var channelConfig = ChannelIn.Mono;
            var audioFormat = Encoding.Pcm16bit;
            int bufferSize = AudioRecord.GetMinBufferSize(sampleRate, channelConfig, audioFormat);
            if (bufferSize < 2048) bufferSize = 2048;

            try
            {
                _audioRecord = new AudioRecord(AudioSource.Mic, sampleRate, channelConfig, audioFormat, bufferSize * 2);
                _audioRecord.StartRecording();
                _isRunning = true;

                _recordingThread = new Thread(AudioRecordingLoop) { IsBackground = true };
                _recordingThread.Start();
                _tts?.Speak("Ultron mobile systems active, sir.");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[Android Audio] Failed to start AudioRecord: {ex.Message}");
            }
        }

        private void AudioRecordingLoop()
        {
            byte[] readBuffer = new byte[1024];

            while (_isRunning && _audioRecord != null)
            {
                int bytesRead = _audioRecord.Read(readBuffer, 0, readBuffer.Length);
                if (bytesRead <= 0) continue;

                // Echo cancellation: Ignore input when Ultron is speaking
                if (_tts != null && _tts.IsSpeaking)
                {
                    _audioBuffer.Clear();
                    _isSpeaking = false;
                    _silenceStart = null;
                    continue;
                }

                // RMS Energy calculation
                float sumSquares = 0f;
                int sampleCount = bytesRead / 2;
                for (int i = 0; i < bytesRead; i += 2)
                {
                    short sample = (short)(readBuffer[i] | (readBuffer[i + 1] << 8));
                    float sampleNorm = sample / 32768f;
                    sumSquares += sampleNorm * sampleNorm;
                }
                float rms = (float)Math.Sqrt(sumSquares / Math.Max(1, sampleCount));

                bool isVoice = rms > _config.EnergyThreshold;
                DateTime now = DateTime.UtcNow;

                if (isVoice)
                {
                    if (!_isSpeaking)
                    {
                        _isSpeaking = true;
                        _audioBuffer.Clear();
                    }
                    _silenceStart = null;
                    for (int i = 0; i < bytesRead; i++) _audioBuffer.Add(readBuffer[i]);
                }
                else if (_isSpeaking)
                {
                    for (int i = 0; i < bytesRead; i++) _audioBuffer.Add(readBuffer[i]);

                    if (_silenceStart == null)
                    {
                        _silenceStart = now;
                    }
                    else if ((now - _silenceStart.Value).TotalSeconds >= _config.SilenceDurationSeconds)
                    {
                        _isSpeaking = false;
                        _silenceStart = null;

                        byte[] pcmData = _audioBuffer.ToArray();
                        _audioBuffer.Clear();

                        double duration = pcmData.Length / (16000.0 * 2.0);
                        if (duration >= 0.25)
                        {
                            byte[] wavBytes = CreateWavBytes(pcmData, 16000, 16, 1);
                            Task.Run(async () => await ProcessSpeechAsync(wavBytes));
                        }
                    }
                }
            }
        }

        private async Task ProcessSpeechAsync(byte[] wavBytes)
        {
            if (_groq == null) return;

            string transcript = await _groq.TranscribeAudioAsync(wavBytes);
            if (string.IsNullOrWhiteSpace(transcript)) return;

            string clean = transcript.Trim();
            string lower = clean.ToLower();

            if (lower == "thank you." || lower == "thank you" || lower == "thanks." || lower.Length <= 2)
                return;

            Console.WriteLine($"[Android Heard] '{clean}'");

            if (!lower.Contains(_config.WakeWord))
                return;

            string command = Regex.Replace(clean, $@"\b{_config.WakeWord}\b", "", RegexOptions.IgnoreCase).Trim();
            if (string.IsNullOrEmpty(command))
            {
                _tts?.Speak("At your service, sir.");
                return;
            }

            var action = await _groq.ClassifyActionAsync(command);
            string reply = "";

            switch (action.Action?.ToLower())
            {
                case "open_app":
                    reply = LaunchAndroidApp(action.App ?? command);
                    break;

                case "chat":
                default:
                    if (lower.Contains("battery"))
                    {
                        reply = GetBatteryStatus();
                    }
                    else if (lower.Contains("flashlight") || lower.Contains("torch"))
                    {
                        reply = ToggleFlashlight(lower.Contains("on"));
                    }
                    else
                    {
                        reply = await _groq.GenerateChatResponseAsync(action.Query ?? command);
                    }
                    break;
            }

            if (!string.IsNullOrWhiteSpace(reply))
            {
                _tts?.Speak(reply);
            }
        }

        private string LaunchAndroidApp(string appName)
        {
            string lower = appName.ToLower();
            string? pkg = null;

            if (lower.Contains("whatsapp")) pkg = "com.whatsapp";
            else if (lower.Contains("youtube")) pkg = "com.google.android.youtube";
            else if (lower.Contains("chrome")) pkg = "com.android.chrome";
            else if (lower.Contains("map")) pkg = "com.google.android.apps.maps";
            else if (lower.Contains("camera")) pkg = "com.google.android.camera";
            else if (lower.Contains("setting")) pkg = "com.android.settings";

            try
            {
                if (pkg != null)
                {
                    var launchIntent = PackageManager?.GetLaunchIntentForPackage(pkg);
                    if (launchIntent != null)
                    {
                        launchIntent.AddFlags(ActivityFlags.NewTask);
                        StartActivity(launchIntent);
                        return $"Opening {appName}, sir.";
                    }
                }

                // Generic launcher
                var intent = new Intent(Intent.ActionMain);
                intent.AddCategory(Intent.CategoryLauncher);
                intent.AddFlags(ActivityFlags.NewTask);
                StartActivity(intent);
                return $"Opening {appName}, sir.";
            }
            catch (Exception ex)
            {
                return $"Could not open {appName}: {ex.Message}";
            }
        }

        private string GetBatteryStatus()
        {
            try
            {
                var filter = new IntentFilter(Intent.ActionBatteryChanged);
                var batteryStatus = RegisterReceiver(null, filter);
                int level = batteryStatus?.GetIntExtra(BatteryManager.ExtraLevel, -1) ?? 100;
                int scale = batteryStatus?.GetIntExtra(BatteryManager.ExtraScale, -1) ?? 100;
                int batteryPct = (int)((level / (float)scale) * 100);
                return $"Your mobile battery is at {batteryPct}%, sir.";
            }
            catch
            {
                return "Battery level status unavailable, sir.";
            }
        }

        private string ToggleFlashlight(bool enable)
        {
            try
            {
                var cameraManager = (CameraManager?)GetSystemService(CameraService);
                if (cameraManager != null)
                {
                    string cameraId = cameraManager.GetCameraIdList()[0];
                    cameraManager.SetTorchMode(cameraId, enable);
                    return enable ? "Flashlight activated, sir." : "Flashlight turned off, sir.";
                }
            }
            catch { }
            return "Could not adjust flashlight on this device.";
        }

        private static byte[] CreateWavBytes(byte[] pcmData, int sampleRate, short bitsPerSample, short channels)
        {
            using var ms = new MemoryStream();
            using var writer = new BinaryWriter(ms);

            writer.Write(new char[4] { 'R', 'I', 'F', 'F' });
            writer.Write(36 + pcmData.Length);
            writer.Write(new char[4] { 'W', 'A', 'V', 'E' });

            writer.Write(new char[4] { 'f', 'm', 't', ' ' });
            writer.Write(16);
            writer.Write((short)1);
            writer.Write(channels);
            writer.Write(sampleRate);
            writer.Write(sampleRate * channels * (bitsPerSample / 8));
            writer.Write((short)(channels * (bitsPerSample / 8)));
            writer.Write(bitsPerSample);

            writer.Write(new char[4] { 'd', 'a', 't', 'a' });
            writer.Write(pcmData.Length);
            writer.Write(pcmData);

            return ms.ToArray();
        }

        private void CreateNotificationChannel()
        {
            if (Build.VERSION.SdkInt >= BuildVersionCodes.O)
            {
                var channel = new NotificationChannel(ChannelId, "Ultron Background Voice", NotificationImportance.Low)
                {
                    Description = "Keeps Ultron listening for commands in the background"
                };
                var manager = (NotificationManager?)GetSystemService(NotificationService);
                manager?.CreateNotificationChannel(channel);
            }
        }

        private Notification BuildNotification(string message)
        {
            if (Build.VERSION.SdkInt >= BuildVersionCodes.O)
            {
                return new Notification.Builder(this, ChannelId)
                    .SetContentTitle("Ultron Autonomous AI")
                    .SetContentText(message)
                    .SetSmallIcon(Resource.Mipmap.appicon)
                    .SetOngoing(true)
                    .Build();
            }
            else
            {
                return new Notification.Builder(this)
                    .SetContentTitle("Ultron Autonomous AI")
                    .SetContentText(message)
                    .SetSmallIcon(Resource.Mipmap.appicon)
                    .SetOngoing(true)
                    .Build();
            }
        }

        public override void OnDestroy()
        {
            _isRunning = false;
            _audioRecord?.Stop();
            _audioRecord?.Release();
            _audioRecord?.Dispose();
            _audioRecord = null;
            _tts?.Dispose();
            base.OnDestroy();
        }
    }
}
