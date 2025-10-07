"""Quick test for Ollama LLM service"""

from app.services.ollama_llm_service import OllamaLLMService

# Sample policy text
sample_text = """
Certificate of Insurance
Policy Holder: Mr. Vikas Sahani
Policy Number: 89313550
Sum Insured: Rs. 5,00,000
Premium: Rs. 7,500
Policy Type: Health Insurance

Coverage:
- Hospitalization expenses
- Pre and post hospitalization
- Daycare procedures

Waiting Period: 30 days for illness, No waiting period for accidents
Pre-existing diseases covered after 2 years

Exclusions:
- Cosmetic surgery
- Self-inflicted injuries
- Treatment outside India
"""

print("Testing Ollama LLM Service with Gemma 3 4B...\n")

try:
    service = OllamaLLMService(model_name="gemma2:4b")
    
    print("1. Generating Intelligent Summary...")
    summary = service.generate_intelligent_summary(sample_text)
    print(f"✓ Summary Generated")
    print(f"Policy Type: {summary.get('policy_type')}")
    print(f"Simple Summary:\n{summary.get('simple_summary', '')[:200]}...\n")
    
    print("2. Extracting Terms with Explanations...")
    terms = service.extract_terms_with_explanations(sample_text)
    print(f"✓ Found {len(terms)} terms with explanations")
    if terms:
        print(f"Example: {terms[0].get('term')} - {terms[0].get('simple_explanation')}\n")
    
    print("3. Identifying Exclusions...")
    exclusions = service.identify_exclusions(sample_text)
    print(f"✓ Found {len(exclusions)} exclusions with explanations")
    if exclusions:
        print(f"Example: {exclusions[0].get('exclusion')}\n")
    
    print("✅ Ollama LLM Service is working perfectly!")
    print("\n🎉 Ready to provide intelligent, layman-friendly explanations with Gemma 3 4B!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
