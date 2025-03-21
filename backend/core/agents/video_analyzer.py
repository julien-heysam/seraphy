import json
import os
import time
import logging

from google import genai

logger = logging.getLogger(__name__)


def generate(action_log_path: str, video_path: str):
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )
    actions_log = json.load(open(action_log_path))
    video_file = client.files.upload(file=video_path)
    # Check whether the file is ready to be used.
    while video_file.state.name == "PROCESSING":
        print('.', end='')
        time.sleep(1)
        video_file = client.files.get(name=video_file.name)

    if video_file.state.name == "FAILED":
        raise ValueError(video_file.state.name)

    print('Done')

    prompt = f"""Analyze the user's actions from the provided JSON and video to generate detailed descriptions and context. Focus on creating key fields for each action:

1. `ts`: The timestamp of the action (keep as is)
2. `description`: A detailed description of the current action
3. `context`: The broader context including:
   - What led to this action (previous steps)
   - The purpose or goal of the action
   - Potential next steps
   - Relevant UI/UX context
   - Context that explains the user's intent, why they are doing what they are doing
   - Questions give example of question that this action could answer, like "where to find all the recordings"

# Output Format
```json
[
{{
  "ts": "original_timestamp",
  "description": "concise_action_description",
  "context": {{
    "previous": "what_led_to_this",
    "purpose": "action_purpose",
    "next": "potential_next_steps",
    "ui_context": "relevant_ui_elements",
    "intent": "user's_underlying_intent",
    "questions": ["example_question_1", "example_question_2"]
  }}
}}
]
```

2. Description Rules:
- Be specific and action-oriented
- Include UI element details
- Use present tense
- Keep it concise (max 50 words)

3. Context Rules:
- Previous: Describe 1-2 preceding actions
- Purpose: Explain the user's goal
- Next: Predict 1-2 likely next actions
- UI Context: Describe surrounding UI elements
- Intent: Explain why the user is doing this
- Questions: List 2-3 relevant questions this action could answer

4. Optimization:
- Use consistent terminology
- Include relevant keywords
- Structure for easy pattern matching
- Make it search-friendly

# Examples

--Input:
```json
{{
  "ts": "21.397629261016846",
  "type": "click",
  "elementUnderCursor": {{
    "classes": "btn-primary",
    "tagName": "button",
    "text": "Submit"
  }},
  "url": "https://app.example.com/form"
}}
```

--Output:
```json`
[
{{
  "ts": "21.397629261016846,
  "description": "User clicks 'Submit' button to complete form",
  "context": {{
    "previous": "User entered data in all form fields",
    "purpose": "To submit the completed application",
    "next": "System will validate and process the submission",
    "ui_context": "Primary action button at bottom of form",
    "intent": "Complete the application process quickly",
    "questions": [
      "How to submit a form?",
      "Where is the submit button located?",
      "What happens after form submission?"
    ]
  }}
}}
]
```

--Input:
```json
{actions_log}
```

--Output:
"""
    # breakpoint()
    response = client.models.generate_content(model="gemini-2.0-pro-exp-02-05", contents=[video_file, prompt])
    logger.info(response.text)

    return response.text


if __name__ == "__main__":
    print(generate("/Users/julienwuthrich/GitHub/seraphy/data/raw/recordings/action_logs/user_actions_20250317_235434.json", "/Users/julienwuthrich/GitHub/seraphy/data/raw/recordings/videos/browser_session_20250317_235434.mp4"))
