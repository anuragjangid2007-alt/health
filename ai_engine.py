import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-3.8-flash:generateContent"
)

MAX_RETRIES = 3
REQUEST_TIMEOUT = 45


def prepare_evidence(evidence):
    """Convert available local evidence into readable text."""

    if not evidence:
        return "No matching local evidence was found."

    evidence_lines = []

    for item in evidence:
        if not isinstance(item, dict):
            continue

        evidence_lines.append(
            f"Title: {item.get('title', 'Unknown')}\n"
            f"Summary: {item.get('summary', 'Not available')}\n"
            f"Source: {item.get('source_name', 'Unknown')}\n"
            f"URL: {item.get('source_url', 'Not available')}"
        )

    if not evidence_lines:
        return "No matching local evidence was found."

    return "\n\n".join(evidence_lines)


def generate_answer(question, evidence):
    """
    Generate general healthcare information in the
    language used by the user.
    """

    question = str(question or "").strip()

    if not question:
        return "Please enter a question.", "FALLBACK"

    if not GEMINI_API_KEY:
        return (
            "AI service is not configured. Please check the "
            "GEMINI_API_KEY setting in your .env file."
        ), "FALLBACK"

    evidence_text = prepare_evidence(evidence)

    prompt = f"""
You are HealthCheck AI, a general-purpose healthcare
information and health-awareness assistant.

YOUR MAIN PURPOSE:
Answer a wide range of health-related questions.
Do not restrict yourself to a predefined list of topics.

USER QUESTION:
{question}

AVAILABLE LOCAL EVIDENCE:
{evidence_text}

1. TOPIC COVERAGE

Try to answer general educational questions about any
health-related topic, including but not limited to:

- Common symptoms and their possible causes
- Fever, headache, cough, cold and digestive problems
- Minor injuries and basic first aid
- Burns, cuts, bruises and wound care
- Diseases, prevention and health awareness
- Nutrition, vitamins, hydration and food safety
- Sleep, exercise and general wellbeing
- Medicines, their general uses and common side effects
- Medical tests and medical terminology
- Children's health, adult health and older people's health
- Oral health, skin health and eye health
- Mental wellbeing and stress
- Hygiene, infections and prevention
- Questions about medical reports or health concepts

This list is illustrative, not restrictive.
If the user asks about another healthcare topic,
try to provide useful general educational information.

2. LANGUAGE

- Detect the language of the user's question.
- For Hindi, answer in natural Hindi using Devanagari.
- For Hinglish, answer in natural Roman Hindi/Hinglish.
- For English, answer in clear, simple English.
- For another language you understand, try to answer
  in that language.
- Do not demand that the user translate the question.

3. ACCURACY AND EVIDENCE

- Give a direct answer first, followed by an explanation.
- Use established medical knowledge carefully.
- Use supplied evidence only when it is relevant.
- Do not claim that a source supports something it does
  not actually say.
- Never invent studies, statistics, citations or URLs.
- Do not claim that you searched the internet if you did not.
- If evidence is missing or uncertain, say so clearly.
- Distinguish general medical knowledge from information
  verified by the available sources.
- Keyword matches alone do not prove a health claim.

4. MEDICAL SAFETY

- Provide educational information, not a diagnosis.
- Explain possible causes without claiming certainty.
- Do not prescribe medicines or personalized dosages.
- Do not recommend starting, stopping or changing
  prescription medicines without a qualified clinician.
- For medication questions, explain general information
  and advise checking the product label and consulting
  a pharmacist or healthcare professional when appropriate.
- For minor injuries, give cautious, basic first-aid guidance.
- For serious wounds, severe burns, breathing difficulty,
  chest pain, loss of consciousness, severe allergic
  reactions or other possible emergencies, advise
  immediate medical assistance.
- Do not delay emergency care by asking unnecessary questions.
- For personal symptoms, mention important warning signs
  and when professional medical assessment is needed.
- Never promise that a treatment will definitely work.

5. RESPONSE STYLE

Use a structure suited to the question:

- Direct answer
- Explanation or possible causes
- Safe steps the user can consider, when appropriate
- Warning signs or when to seek medical help
- Evidence limitations, when relevant

Keep simple questions concise and explain complicated
topics in more detail.

Do not force every section into every answer.
If the question is not health-related, politely explain
that HealthCheck AI is designed for healthcare questions.

End with a brief reminder when appropriate that the
information is educational and is not a medical diagnosis.

Answer the user's actual question in the user's language.
"""

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                GEMINI_URL,
                params={"key": GEMINI_API_KEY},
                json={
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt}
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 1200
                    }
                },
                timeout=REQUEST_TIMEOUT
            )

            response.raise_for_status()
            data = response.json()

            candidates = data.get("candidates", [])

            if not candidates:
                raise ValueError("No answer candidate returned")

            parts = (
                candidates[0]
                .get("content", {})
                .get("parts", [])
            )

            answer = "\n".join(
                part.get("text", "")
                for part in parts
                if part.get("text")
            ).strip()

            if not answer:
                raise ValueError("The AI returned an empty answer")

            return answer, "AI"

        except requests.RequestException as error:
            print(
                f"Gemini request failed "
                f"(attempt {attempt + 1}): "
                f"{type(error).__name__}"
            )

            if isinstance(error, requests.HTTPError):
                if error.response is not None:
                    print(
                        "HTTP status:",
                        error.response.status_code
                    )

            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)

        except (ValueError, KeyError, IndexError, TypeError) as error:
            print(
                "Gemini response processing failed:",
                type(error).__name__
            )
            break

    fallback_answer = (
        "HealthCheck AI ka AI service abhi jawab generate "
        "nahi kar pa raha hai. Kripya kuch der baad dobara "
        "try karein. Available evidence sources ko dekh sakte "
        "hain, lekin sirf keyword match hone se health claim "
        "verify nahi hota. Personal medical advice ke liye "
        "qualified healthcare professional se consult karein."
    )

    return fallback_answer, "FALLBACK"