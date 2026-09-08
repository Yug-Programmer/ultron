using System;
using System.Text.RegularExpressions;
using System.Threading.Tasks;

namespace Ultron.Shared.Memory
{
    public class PersonalizationEngine
    {
        private readonly MemoryService _memory;

        public PersonalizationEngine(MemoryService? memory = null)
        {
            _memory = memory ?? MemoryService.Instance;
        }

        public async Task<string?> TryHandleExplicitMemoryCommandAsync(string text)
        {
            if (string.IsNullOrWhiteSpace(text))
                return null;

            string lower = text.ToLower().Trim();

            // 1. "Remember that..." or "Yaad rakhna ki..."
            var rememberMatch = Regex.Match(text, @"(?:remember\s+that|remember|yaad\s+rakhna\s+ki|yaad\s+rakho\s+ki)\s+(.*)", RegexOptions.IgnoreCase);
            if (rememberMatch.Success)
            {
                string fact = rememberMatch.Groups[1].Value.Trim();
                if (!string.IsNullOrEmpty(fact))
                {
                    // Derive a concise key and value
                    string key = "Fact_" + DateTime.UtcNow.ToString("yyyyMMdd_HHmmss");
                    if (fact.Contains("favorite", StringComparison.OrdinalIgnoreCase) || fact.Contains("favourite", StringComparison.OrdinalIgnoreCase))
                    {
                        key = "Favorite Preference";
                    }
                    else if (fact.Contains("my name is", StringComparison.OrdinalIgnoreCase) || fact.Contains("mera naam", StringComparison.OrdinalIgnoreCase))
                    {
                        key = "User Name";
                    }
                    else if (fact.Contains("project", StringComparison.OrdinalIgnoreCase) || fact.Contains("working on", StringComparison.OrdinalIgnoreCase))
                    {
                        key = "Current Project";
                    }

                    await _memory.LearnUserFactAsync(key, fact);
                    return $"I have committed that to memory, sir: \"{fact}\".";
                }
            }

            // 2. "What do you know about me?" / "Who am I?" / "Mere baare me kya jante ho?"
            if (lower.Contains("what do you know about me") || lower.Contains("who am i") || lower.Contains("mere baare me") || lower.Contains("my profile"))
            {
                var facts = await _memory.GetUserFactsAsync();
                if (facts.Count == 0)
                    return "I have not logged any personal preferences yet, sir. You can tell me 'Ultron, remember that...' at any time.";

                var list = string.Join("; ", facts.ConvertAll(f => $"{f.Key}: {f.Value}"));
                return $"Here is what I have learned about you, sir: {list}.";
            }

            // 3. "What was I doing?" / "What was I working on?" / "Summarize my day/work"
            if (lower.Contains("what was i doing") || lower.Contains("what was i working on") || lower.Contains("summarize my day") || lower.Contains("screen activity") || lower.Contains("kya kar raha tha"))
            {
                string summary = await _memory.FormatTimelineSummaryAsync(hours: 12);
                return summary;
            }

            return null;
        }
    }
}
