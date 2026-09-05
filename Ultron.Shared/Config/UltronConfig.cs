using System;
using System.IO;
using System.Text.Json;

namespace Ultron.Shared.Config
{
    public class UltronConfig
    {
        public string GroqApiKey { get; set; } = "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";
        public string SttModel { get; set; } = "whisper-large-v3-turbo";
        public string LlmModel { get; set; } = "qwen/qwen3.8-27b";
        public string WakeWord { get; set; } = "ultron";
        public float EnergyThreshold { get; set; } = 0.015f;
        public double SilenceDurationSeconds { get; set; } = 0.35;
        public string TtsVoice { get; set; } = "Microsoft David Desktop";
        public int TtsRate { get; set; } = 1;

        public static UltronConfig Load(string path = "config.json")
        {
            try
            {
                if (File.Exists(path))
                {
                    string json = File.ReadAllText(path);
                    return JsonSerializer.Deserialize<UltronConfig>(json) ?? new UltronConfig();
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[Config] Warning: Failed to load {path} ({ex.Message}). Using defaults.");
            }

            var cfg = new UltronConfig();
            Save(cfg, path);
            return cfg;
        }

        public static void Save(UltronConfig config, string path = "config.json")
        {
            try
            {
                string json = JsonSerializer.Serialize(config, new JsonSerializerOptions { WriteIndented = true });
                File.WriteAllText(path, json);
            }
            catch { }
        }
    }
}
