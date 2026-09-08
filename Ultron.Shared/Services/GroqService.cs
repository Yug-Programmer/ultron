using System;
using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using Ultron.Shared.Config;

namespace Ultron.Shared.Services
{
    public class ActionCommand
    {
        public string Action { get; set; } = "chat";
        public string? Text { get; set; }
        public string? Find { get; set; }
        public string? Replace { get; set; }
        public string? Scope { get; set; }
        public string? App { get; set; }
        public string? Folder { get; set; }
        public string? File { get; set; }
        public string? Instruction { get; set; }
        public string? Query { get; set; }
    }

    public class GroqService
    {
        private readonly HttpClient _httpClient;
        private readonly UltronConfig _config;

        private const string ActionClassifierSystemPrompt = @"You are Ultron's Neural Action Classifier. Convert the user's spoken command into an executable JSON action object.
Supported actions:
1. {""action"": ""type"", ""text"": ""<text_to_type>""} - when user wants to type or write text into the active app/note
2. {""action"": ""replace_in_app"", ""find"": ""<find_text>"", ""replace"": ""<replace_text>""} - when user wants to replace/change text in active window
3. {""action"": ""clear_in_app""} - when user wants to clear or delete all text in active window
4. {""action"": ""delete_in_app"", ""scope"": ""word"" | ""line""} - when user wants to delete word or line
5. {""action"": ""undo""} / {""action"": ""redo""}
6. {""action"": ""save""}
7. {""action"": ""open_app"", ""app"": ""<app_name>""}
8. {""action"": ""open_folder"", ""folder"": ""<folder_name>""}
9. {""action"": ""modify_file"", ""file"": ""<filename>"", ""instruction"": ""<instruction>""}
10. {""action"": ""delete_file"", ""file"": ""<filename>""}
11. {""action"": ""chat"", ""query"": ""<user_query>""} - for questions, general talk, news, etc.

Return ONLY a valid JSON object. Do not include markdown codeblocks or explanation.";

        public GroqService(UltronConfig config)
        {
            _config = config;
            _httpClient = new HttpClient { Timeout = TimeSpan.FromSeconds(15) };
        }

        public async Task<string> TranscribeAudioAsync(byte[] wavBytes)
        {
            if (wavBytes == null || wavBytes.Length == 0)
                return string.Empty;

            try
            {
                using var request = new HttpRequestMessage(HttpMethod.Post, "https://api.groq.com/openai/v1/audio/transcriptions");
                request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _config.GroqApiKey);

                using var content = new MultipartFormDataContent();
                var audioContent = new ByteArrayContent(wavBytes);
                audioContent.Headers.ContentType = MediaTypeHeaderValue.Parse("audio/wav");
                content.Add(audioContent, "file", "audio.wav");
                content.Add(new StringContent(_config.SttModel), "model");
                // Omit language parameter to let Whisper automatically detect English, Hindi, Hinglish, etc.
                content.Add(new StringContent("Ultron, Jarvis, New Volume Y, Local Disk C, Program Files, Notepad, Word, Excel, Task Manager, file, WhatsApp, YouTube, kholo, likho, save karo, delete karo, change karo."), "prompt");
                content.Add(new StringContent("0.0"), "temperature");
                content.Add(new StringContent("json"), "response_format");

                request.Content = content;
                var response = await _httpClient.SendAsync(request);
                string jsonString = await response.Content.ReadAsStringAsync();

                if (response.IsSuccessStatusCode)
                {
                    using var doc = JsonDocument.Parse(jsonString);
                    if (doc.RootElement.TryGetProperty("text", out var textProp))
                    {
                        return textProp.GetString()?.Trim() ?? string.Empty;
                    }
                }
                else
                {
                    Console.WriteLine($"[Groq STT] Error {response.StatusCode}: {jsonString}");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[Groq STT] Exception: {ex.Message}");
            }

            return string.Empty;
        }

        public async Task<ActionCommand> ClassifyActionAsync(string userSpeech)
        {
            try
            {
                using var request = new HttpRequestMessage(HttpMethod.Post, "https://api.groq.com/openai/v1/chat/completions");
                request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _config.GroqApiKey);

                var payload = new
                {
                    model = _config.LlmModel,
                    messages = new[]
                    {
                        new { role = "system", content = ActionClassifierSystemPrompt },
                        new { role = "user", content = userSpeech }
                    },
                    temperature = 0.0,
                    max_tokens = 150
                };

                string jsonPayload = JsonSerializer.Serialize(payload);
                request.Content = new StringContent(jsonPayload, Encoding.UTF8, "application/json");

                var response = await _httpClient.SendAsync(request);
                string responseBody = await response.Content.ReadAsStringAsync();

                if (response.IsSuccessStatusCode)
                {
                    using var doc = JsonDocument.Parse(responseBody);
                    string rawContent = doc.RootElement.GetProperty("choices")[0].GetProperty("message").GetProperty("content").GetString() ?? "";

                    rawContent = Regex.Replace(rawContent, @"^```[a-zA-Z]*\s*", "", RegexOptions.Multiline);
                    rawContent = Regex.Replace(rawContent, @"\s*```$", "", RegexOptions.Multiline).Trim();

                    var parsed = JsonSerializer.Deserialize<ActionCommand>(rawContent, new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
                    if (parsed != null)
                        return parsed;
                }
                else
                {
                    Console.WriteLine($"[Groq Classifier] Error {response.StatusCode}: {responseBody}");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[Groq Classifier] Exception: {ex.Message}");
            }

            return new ActionCommand { Action = "chat", Query = userSpeech };
        }

        public async Task<string> GenerateChatResponseAsync(string query, string systemContext = "")
        {
            try
            {
                using var request = new HttpRequestMessage(HttpMethod.Post, "https://api.groq.com/openai/v1/chat/completions");
                request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _config.GroqApiKey);

                string sysPrompt = "You are Ultron, an advanced, highly intelligent, and direct AI assistant. Speak concisely, authoritatively, and with confidence without conversational filler.";
                if (!string.IsNullOrEmpty(systemContext))
                {
                    sysPrompt += $"\n\nContext:\n{systemContext}";
                }

                var payload = new
                {
                    model = _config.LlmModel,
                    messages = new[]
                    {
                        new { role = "system", content = sysPrompt },
                        new { role = "user", content = query }
                    },
                    temperature = 0.6,
                    max_tokens = 300
                };

                string jsonPayload = JsonSerializer.Serialize(payload);
                request.Content = new StringContent(jsonPayload, Encoding.UTF8, "application/json");

                var response = await _httpClient.SendAsync(request);
                string responseBody = await response.Content.ReadAsStringAsync();

                if (response.IsSuccessStatusCode)
                {
                    using var doc = JsonDocument.Parse(responseBody);
                    string reply = doc.RootElement.GetProperty("choices")[0].GetProperty("message").GetProperty("content").GetString() ?? "";
                    
                    reply = Regex.Replace(reply, @"<think>.*?</think>", "", RegexOptions.Singleline);
                    reply = reply.Replace("*", "").Replace("#", "").Trim();
                    return reply;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[Groq Chat] Exception: {ex.Message}");
            }

            return "I am operational, sir. How may I assist you?";
        }
    }
}
