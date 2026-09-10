from google import genai

client = genai.Client(api_key="AQ.Ab8RN6L4Ud1dvXSt-mUpCssduHwejlfueSCPvQO61qPsnnW6YA")

interaction = client.interactions.create(
    model="gemini-3.7-flash",
    input="Explain how AI works in a few words"
)
print(interaction.output_text)