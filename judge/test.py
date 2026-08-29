from google import genai

client = genai.Client(api_key="AQ.Ab8RN6K5yU3LXsLNESqKQ9dJ1eVeFQ-FRV8IW7hJ_khj8pw7JQ")

interaction = client.interactions.create(
    model="gemini-3.7-flash",
    input="Explain how AI works in a few words"
)
print(interaction.output_text)