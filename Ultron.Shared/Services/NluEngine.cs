using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using Ultron.Shared.Config;
using Ultron.Shared.Memory;

namespace Ultron.Shared.Services
{
    public class NluResult
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
        public string Language { get; set; } = "en";
        public string ReplyLanguage { get; set; } = "en";
    }

    public class DialogueContext
    {
        public string? LastActiveApp { get; set; }
        public string? LastActiveFile { get; set; }
        public string? LastTypedText { get; set; }
        public string? LastCommand { get; set; }
        public string? LastLanguage { get; set; } = "en";

        public void Update(NluResult result, string rawInput)
        {
            LastCommand = rawInput;
            LastLanguage = result.Language;

            if (!string.IsNullOrEmpty(result.App))
                LastActiveApp = result.App;

            if (!string.IsNullOrEmpty(result.File))
                LastActiveFile = result.File;

            if (!string.IsNullOrEmpty(result.Text))
                LastTypedText = result.Text;
        }
    }

    public class NluEngine
    {
        private readonly HttpClient _httpClient;
        private readonly UltronConfig _config;
        private readonly DialogueContext _context = new();
        private readonly PersonalizationEngine _personalization = new();

        private const string LocalNlpUrl = "http://127.0.0.1:8766/nlp/analyze";

        private const string MultilingualNlpSystemPrompt = @"You are Ultron's Multilingual Neural NLP Engine.
Your job is to analyze the user's natural language input (English, Hindi, Hinglish, etc.) and extract structured intent, entities, and context.
Resolve any pronouns ('it', 'this', 'that', 'isme', 'isko', 'usme') using the provided conversation context.

Supported actions:
1. {""action"": ""type"", ""text"": ""<text_to_type>"", ""language"": ""<lang>"", ""reply_language"": ""<lang>""}
   - When user wants to write, type, or dictate text (e.g., 'write hello', 'isme hello likho')
2. {""action"": ""replace_in_app"", ""find"": ""<find_text>"", ""replace"": ""<replace_text>"", ""language"": ""<lang>"", ""reply_language"": ""<lang>""}
   - When user wants to replace/change text (e.g., 'replace apple with orange', 'apple ko orange se badal do')
3. {""action"": ""clear_in_app"", ""language"": ""<lang>"", ""reply_language"": ""<lang>""}
   - When user wants to clear or delete all text in current window
4. {""action"": ""delete_in_app"", ""scope"": ""word"" | ""line"", ""language"": ""<lang>"", ""reply_language"": ""<lang>""}
   - When user wants to delete word or line
5. {""action"": ""undo""} / {""action"": ""redo""}
6. {""action"": ""save"", ""language"": ""<lang>"", ""reply_language"": ""<lang>""}
   - When user wants to save active document (e.g., 'save file', 'isko save karo')
7. {""action"": ""open_app"", ""app"": ""<app_name>"", ""language"": ""<lang>"", ""reply_language"": ""<lang>""}
   - When user wants to open an application (e.g., 'open notepad', 'notepad kholo')
8. {""action"": ""open_folder"", ""folder"": ""<folder_name>"", ""language"": ""<lang>"", ""reply_language"": ""<lang>""}
   - When user wants to open a folder or drive (e.g., 'open local disk c', 'c drive kholo')
9. {""action"": ""modify_file"", ""file"": ""<filename>"", ""instruction"": ""<instruction>"", ""language"": ""<lang>"", ""reply_language"": ""<lang>""}
   - When user wants to edit a file on disk (e.g., 'in notes.txt add bullet points', 'notes.txt me meeting add karo')
10. {""action"": ""delete_file"", ""file"": ""<filename>"", ""language"": ""<lang>"", ""reply_language"": ""<lang>""}
11. {""action"": ""vitals"", ""language"": ""<lang>"", ""reply_language"": ""<lang>""}
   - When user asks about battery, CPU, RAM, or storage (e.g., 'what is my battery', 'battery kitni hai')
12. {""action"": ""recall_activity"", ""language"": ""<lang>"", ""reply_language"": ""<lang>""}
   - When user asks what they were doing, what they worked on, screen history (e.g., 'what was I doing 10 minutes ago', 'summarize my activity')
13. {""action"": ""remember_fact"", ""text"": ""<fact>"", ""language"": ""<lang>"", ""reply_language"": ""<lang>""}
   - When user asks to memorize a fact or preference (e.g., 'remember that my favorite tool is vs code', 'yaad rakhna ki...')
14. {""action"": ""who_am_i"", ""language"": ""<lang>"", ""reply_language"": ""<lang>""}
   - When user asks what is known about them or their profile (e.g., 'who am i', 'what do you know about me')
15. {""action"": ""chat"", ""query"": ""<user_query>"", ""language"": ""<lang>"", ""reply_language"": ""<lang>""}
   - For questions, explanations, talk, news, weather, or greeting.

Output must be raw valid JSON only. No markdown formatting, backticks, or explanation.";

        public DialogueContext Context => _context;
        public PersonalizationEngine Personalization => _personalization;

        public NluEngine(UltronConfig config)
        {
            _config = config;
            _httpClient = new HttpClient { Timeout = TimeSpan.FromSeconds(10) };
        }

        public async Task<NluResult> UnderstandAsync(string userSpeech)
        {
            if (string.IsNullOrWhiteSpace(userSpeech))
                return new NluResult { Action = "chat", Query = "" };

            // 0. Instant memory intent evaluation (<1ms)
            string lower = userSpeech.ToLower().Trim();
            if (lower.StartsWith("remember that ") || lower.StartsWith("remember ") || lower.StartsWith("yaad rakhna ki ") || lower.StartsWith("yaad rakho ki "))
            {
                var match = Regex.Match(userSpeech, @"(?:remember\s+that|remember|yaad\s+rakhna\s+ki|yaad\s+rakho\s+ki)\s+(.*)", RegexOptions.IgnoreCase);
                if (match.Success)
                {
                    var res = new NluResult { Action = "remember_fact", Text = match.Groups[1].Value.Trim() };
                    _context.Update(res, userSpeech);
                    return res;
                }
            }
            if (lower.Contains("what do you know about me") || lower.Contains("who am i") || lower.Contains("mere baare me kya jante ho"))
            {
                var res = new NluResult { Action = "who_am_i" };
                _context.Update(res, userSpeech);
                return res;
            }
            if (lower.Contains("what was i doing") || lower.Contains("what was i working on") || lower.Contains("summarize my day") || lower.Contains("screen activity") || lower.Contains("kya kar raha tha"))
            {
                var res = new NluResult { Action = "recall_activity" };
                _context.Update(res, userSpeech);
                return res;
            }

            // 1. Check Local Python NLP Service first (<20ms response if running)
            var localResult = await TryLocalPythonNlpAsync(userSpeech);
            if (localResult != null)
            {
                _context.Update(localResult, userSpeech);
                return localResult;
            }

            // 2. Fall back to Groq Cloud Multilingual Neural NLP Engine
            var groqResult = await QueryGroqNluAsync(userSpeech);
            _context.Update(groqResult, userSpeech);
            return groqResult;
        }

        private async Task<NluResult?> TryLocalPythonNlpAsync(string text)
        {
            try
            {
                using var cts = new System.Threading.CancellationTokenSource(250);
                var payload = new { text = text, last_app = _context.LastActiveApp, last_file = _context.LastActiveFile };
                string json = JsonSerializer.Serialize(payload);
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                var resp = await _httpClient.PostAsync(LocalNlpUrl, content, cts.Token);
                if (resp.IsSuccessStatusCode)
                {
                    string body = await resp.Content.ReadAsStringAsync();
                    return JsonSerializer.Deserialize<NluResult>(body, new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
                }
            }
            catch
            {
                // Local Python service offline; seamlessly falls through to cloud NLP
            }
            return null;
        }

        private async Task<NluResult> QueryGroqNluAsync(string text)
        {
            try
            {
                using var request = new HttpRequestMessage(HttpMethod.Post, "https://api.groq.com/openai/v1/chat/completions");
                request.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", _config.GroqApiKey);

                string memSummary = await MemoryService.Instance.GetPersonalizedContextSummaryAsync();
                string contextPrompt = $"Context: LastActiveApp='{_context.LastActiveApp ?? "none"}', LastActiveFile='{_context.LastActiveFile ?? "none"}', LastTyped='{_context.LastTypedText ?? "none"}'.\n{memSummary}";

                var payload = new
                {
                    model = _config.LlmModel,
                    messages = new[]
                    {
                        new { role = "system", content = $"{MultilingualNlpSystemPrompt}\n\n{contextPrompt}" },
                        new { role = "user", content = text }
                    },
                    temperature = 0.0,
                    max_tokens = 200
                };

                string jsonPayload = JsonSerializer.Serialize(payload);
                request.Content = new StringContent(jsonPayload, Encoding.UTF8, "application/json");

                var response = await _httpClient.SendAsync(request);
                string responseBody = await response.Content.ReadAsStringAsync();

                if (response.IsSuccessStatusCode)
                {
                    using var doc = JsonDocument.Parse(responseBody);
                    string raw = doc.RootElement.GetProperty("choices")[0].GetProperty("message").GetProperty("content").GetString() ?? "";

                    raw = Regex.Replace(raw, @"^```[a-zA-Z]*\s*", "", RegexOptions.Multiline);
                    raw = Regex.Replace(raw, @"\s*```$", "", RegexOptions.Multiline).Trim();

                    var parsed = JsonSerializer.Deserialize<NluResult>(raw, new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
                    if (parsed != null)
                        return parsed;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[NLU Engine] Notice: {ex.Message}");
            }

            return new NluResult { Action = "chat", Query = text, Language = "en", ReplyLanguage = "en" };
        }
    }
}
