# Create a comprehensive documentation for bot tables and upload to OpenAI Assistant
# This will provide context for the AI to better understand the structure when analyzing empty cells

# First, generate the documentation
python generate_tables_docs.py --empty-cells

# Then upload it to the OpenAI Assistant
python upload_to_assistant.py

# This script assumes you have set OPENAI_API_KEY and OPENAI_ASSISTANT_ID in your .env file
