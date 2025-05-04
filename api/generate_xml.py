# api/generate_xml.py

import json
import openai
from config.settings import OPENAI_API_KEY, OPENAI_MODEL

# Setup OpenAI API key
openai.api_key = OPENAI_API_KEY

def generate_xml_from_comment(comment_text, xml_snippet=None):
    """
    Sends the comment text and optionally an XML snippet to OpenAI
    and gets back the corrected XML.
    """

    try:
        # Build the system and user messages dynamically
        system_prompt = "You are an expert technical writer for SAP Help Portal. Your task is to update XML content based on comments."
        
        user_prompt = f"""
You are given a comment about an SAP Help Portal page and the existing XML snippet related to it.

Comment:
{comment_text}

Existing XML:
{xml_snippet}
            

Task:
Update or improve the XML based on the comment, keeping SAP documentation standards.
Only output the corrected XML snippet without any explanations.
"""



        response = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        # Extract the XML content
        xml_content = response.choices[0].message.content.strip()
        return xml_content

    except Exception as e:
        print(f"Error generating XML: {e}")
        return None
    
# response = openai.chat.completions.create(
#     model="gpt-4o-mini-2025-04-16",
#     response_format={"type": "json_object"},
#     messages=[
#       {"role":"system",
#        "content":"You are an SAP help-portal technical writer…"},
#       {"role":"user",
#        "content":json.dumps({
#          "comment": comment_text,
#          "snippet": xml_snippet
#        })}
#     ],
#     functions=[
#       {
#         "name":"apply_patch",
#         "parameters":{
#           "type":"object",
#           "properties":{
#             "replacement_xml":{"type":"string"}
#           },
#           "required":["replacement_xml"]
#         }
#       }
#     ],
#     temperature=0.2
# )
# patched = response.choices[0].message.function_call.arguments["replacement_xml"]


# Quick test
if __name__ == "__main__":
    test_comment = "Please mention that notification services should also be configured."
    test_snippet = """
<step id="configuration">
    <title>Subscription Management Setup</title>
    <p>The subscription management configuration must be updated.</p>
</step>
"""
    xml_result = generate_xml_from_comment(test_comment, test_snippet)
    print("\nGenerated Corrected XML:\n", xml_result)
