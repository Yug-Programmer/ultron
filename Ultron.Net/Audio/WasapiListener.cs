using System;
using System.Collections.Generic;
using System.IO;
using NAudio.Wave;
using Ultron.Shared.Config;
using Ultron.Net.Services;

namespace Ultron.Net.Audio
{
    public class WasapiListener : IDisposable
    {
        private readonly UltronConfig _config;
        private readonly TtsService _tts;
        private WaveIn? _waveIn;
        private readonly List<byte> _audioBuffer = new();
        private bool _isSpeaking = false;
        private DateTime? _silenceStart = null;
        private DateTime _lastTtsEnd = DateTime.MinValue;

        public event Action<byte[]>? OnSpeechCaptured;
        public event Action<float>? OnVolumeLevel;

        public WasapiListener(UltronConfig config, TtsService tts)
        {
            _config = config;
            _tts = tts;
            _tts.OnSpeechCompleted += () => _lastTtsEnd = DateTime.UtcNow;
        }

        public void Start()
        {
            if (_waveIn != null)
                return;

            _waveIn = new WaveIn
            {
                WaveFormat = new WaveFormat(16000, 16, 1),
                BufferMilliseconds = 80
            };

            _waveIn.DataAvailable += OnDataAvailable;
            _waveIn.StartRecording();
            Console.WriteLine("[Audio] Low-latency WASAPI audio capture started (16kHz 16-bit Mono).");
        }

        public void Stop()
        {
            if (_waveIn != null)
            {
                _waveIn.StopRecording();
                _waveIn.DataAvailable -= OnDataAvailable;
                _waveIn.Dispose();
                _waveIn = null;
                Console.WriteLine("[Audio] WASAPI audio capture stopped.");
            }
        }

        private void OnDataAvailable(object? sender, WaveInEventArgs e)
        {
            // Acoustic Echo Cancellation: Mute microphone while Ultron speaks
            if (_tts.IsSpeaking)
            {
                _audioBuffer.Clear();
                _isSpeaking = false;
                _silenceStart = null;
                return;
            }

            // Reverberation grace period: 200ms after Ultron stops speaking
            if ((DateTime.UtcNow - _lastTtsEnd).TotalMilliseconds < 200)
            {
                _audioBuffer.Clear();
                _isSpeaking = false;
                _silenceStart = null;
                return;
            }

            // Calculate RMS energy
            float sumSquares = 0f;
            int sampleCount = e.BytesRecorded / 2;
            for (int i = 0; i < e.BytesRecorded; i += 2)
            {
                short sample = (short)(e.Buffer[i] | (e.Buffer[i + 1] << 8));
                float sampleNorm = sample / 32768f;
                sumSquares += sampleNorm * sampleNorm;
            }

            float rms = (float)Math.Sqrt(sumSquares / Math.Max(1, sampleCount));
            OnVolumeLevel?.Invoke(rms);

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
                for (int i = 0; i < e.BytesRecorded; i++)
                {
                    _audioBuffer.Add(e.Buffer[i]);
                }
            }
            else if (_isSpeaking)
            {
                for (int i = 0; i < e.BytesRecorded; i++)
                {
                    _audioBuffer.Add(e.Buffer[i]);
                }

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

                    // Filter out short noise blips (<0.3s)
                    double durationSeconds = pcmData.Length / (16000.0 * 2.0);
                    if (durationSeconds >= 0.25)
                    {
                        byte[] wavBytes = CreateWavBytes(pcmData, 16000, 16, 1);
                        OnSpeechCaptured?.Invoke(wavBytes);
                    }
                }
            }
        }

        private static byte[] CreateWavBytes(byte[] pcmData, int sampleRate, short bitsPerSample, short channels)
        {
            using var ms = new MemoryStream();
            using var writer = new BinaryWriter(ms);

            // RIFF header
            writer.Write(new char[4] { 'R', 'I', 'F', 'F' });
            writer.Write(36 + pcmData.Length);
            writer.Write(new char[4] { 'W', 'A', 'V', 'E' });

            // fmt subchunk
            writer.Write(new char[4] { 'f', 'm', 't', ' ' });
            writer.Write(16); // Subchunk1Size (16 for PCM)
            writer.Write((short)1); // AudioFormat (1 for PCM)
            writer.Write(channels);
            writer.Write(sampleRate);
            writer.Write(sampleRate * channels * (bitsPerSample / 8)); // ByteRate
            writer.Write((short)(channels * (bitsPerSample / 8))); // BlockAlign
            writer.Write(bitsPerSample);

            // data subchunk
            writer.Write(new char[4] { 'd', 'a', 't', 'a' });
            writer.Write(pcmData.Length);
            writer.Write(pcmData);

            return ms.ToArray();
        }

        public void Dispose()
        {
            Stop();
        }
    }
}
