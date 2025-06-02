# ClassifierAgent: Detects format and business intent, routes input

class ClassifierAgent:
    def __init__(self, memory):
        self.memory = memory

    def _extract_text_from_image(self, image_data):
        """Extract text from image using OCR."""
        try:
            import pytesseract
            from PIL import Image
            import io
            
            # Convert bytes to image
            image = Image.open(io.BytesIO(image_data))
            # Extract text using Tesseract OCR
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            return None

    def _process_image_file(self, input_data):
        """Process image file and extract text."""
        try:
            with open(input_data, 'rb') as f:
                image_data = f.read()
            return self._extract_text_from_image(image_data)
        except Exception as e:
            return None

    def classify(self, input_data, source):
        """
        Detects format (PDF, Email, JSON, Image) and business intent (RFQ, Complaint, Invoice, Regulation, Fraud Risk).
        Uses few-shot examples and pattern matching for classification.
        Returns dict with format, intent, confidence scores, and metadata.
        """
        import os
        import json
        import mimetypes
        try:
            import openai
        except ImportError:
            openai = None
            
        # Check if input is an image
        is_image = False
        if isinstance(input_data, str) and os.path.exists(input_data):
            mime_type, _ = mimetypes.guess_type(input_data)
            is_image = mime_type and mime_type.startswith('image/')
        elif isinstance(input_data, (bytes, bytearray)):
            is_image = True
        # Format detection (for prompt context)
        format = None
        metadata = {}
        text_blob = ""
        
        try:
            if is_image or (isinstance(input_data, str) and any(input_data.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff'])):
                format = 'Image'
                if isinstance(input_data, str):
                    text_blob = self._process_image_file(input_data) or ""
                else:
                    text_blob = self._extract_text_from_image(input_data) or ""
                metadata['is_image'] = True
                if not text_blob:
                    metadata['ocr_warning'] = "No text could be extracted from the image"
                    
            elif source == 'PDF' or (isinstance(input_data, str) and input_data.lower().endswith('.pdf')):
                format = 'PDF'
                try:
                    from PyPDF2 import PdfReader
                    reader = PdfReader(input_data)
                    text_blob = '\n'.join([page.extract_text() or '' for page in reader.pages])
                except Exception as e:
                    text_blob = ''
                    metadata['pdf_error'] = str(e)
                    
            elif source == 'Email' or (isinstance(input_data, str) and input_data.lower().endswith('.eml')):
                format = 'Email'
                try:
                    with open(input_data, 'r', encoding='utf-8', errors='ignore') as f:
                        text_blob = f.read()
                except Exception as e:
                    text_blob = ''
                    metadata['email_error'] = str(e)
                    
            elif source == 'JSON' or isinstance(input_data, dict):
                format = 'JSON'
                text_blob = json.dumps(input_data)
                
            else:
                format = 'Unknown'
                text_blob = str(input_data)
                
        except Exception as e:
            format = format or 'Unknown'
            metadata['format_detection_error'] = str(e)
            text_blob = str(input_data)
        # LLM prompt
        prompt = (
            "You are a smart document classifier.\n"
            "Detect the format (PDF, Email, JSON) and business intent (RFQ, Complaint, Invoice, Regulation, Fraud Risk) for the following input.\n"
            "Respond as JSON: {\"format\":..., \"intent\":..., \"metadata\":...}.\n"
            "Input: \n" + text_blob[:2000]  # Limit input size for LLM
        )
        llm_result = None
        if openai and os.environ.get('GROQ_API_KEY'):
            try:
                # Configure for Groq API
                groq_api_key = os.environ['GROQ_API_KEY']
                model_name = os.environ.get('GROQ_MODEL', 'llama3-8b-8192')  # Default to a valid model
                
                # Initialize the client with Groq's endpoint
                client = openai.OpenAI(
                    api_key=groq_api_key,
                    base_url='https://api.groq.com/openai/v1'
                )
                
                # Make the API call with proper error handling
                try:
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant that classifies documents."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.0,
                        max_tokens=1000,
                        timeout=30
                    )
                    
                    # Extract and parse the response
                    if response.choices and len(response.choices) > 0:
                        content = response.choices[0].message.content
                        try:
                            # Try to find JSON in markdown code blocks
                            import re
                            json_match = re.search(r'```(?:json\n)?(.*?)\n```', content, re.DOTALL)
                            if json_match:
                                content = json_match.group(1).strip()
                            
                            # Try to parse the response as JSON
                            llm_result = json.loads(content)
                            
                            # Ensure the required fields exist
                            if not isinstance(llm_result, dict) or 'format' not in llm_result or 'intent' not in llm_result:
                                raise ValueError("Response missing required fields")
                                
                        except (json.JSONDecodeError, ValueError) as e:
                            # If response isn't valid JSON or missing fields, try to extract format and intent from text
                            format_match = re.search(r'"format"\s*:\s*"([^"]+)"', content)
                            intent_match = re.search(r'"intent"\s*:\s*"([^"]+)"', content)
                            
                            if format_match and intent_match:
                                llm_result = {
                                    "format": format_match.group(1),
                                    "intent": intent_match.group(1),
                                    "metadata": {"warning": "Extracted from text response"}
                                }
                            else:
                                # If we can't extract the fields, create a fallback result
                                raise ValueError("Could not extract required fields from response")
                except openai.APIError as e:
                    # Handle API-specific errors
                    llm_result = {
                        "format": "Unknown",
                        "intent": "Unknown",
                        "metadata": {
                            "error": "API Error",
                            "error_details": str(e)
                        }
                    }
                except Exception as e:
                    # Handle other unexpected errors
                    llm_result = {
                        "format": "Unknown",
                        "intent": "Unknown",
                        "metadata": {
                            "error": "Unexpected error",
                            "error_details": str(e)
                        }
                    }
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                metadata['llm_error'] = f"{str(e)}\n\n{error_trace}"
                print(f"Error in Groq API initialization: {str(e)}")
                print(traceback.format_exc())
                # Set a fallback result if there was an error initializing the client
                llm_result = {
                    "format": "Unknown",
                    "intent": "Unknown",
                    "metadata": {
                        "error": "Failed to initialize API client",
                        "error_details": str(e)
                    }
                }
        # Ensure we have a valid result with format and intent
        result = {
            'format': 'Unknown',
            'intent': 'Unknown',
            'metadata': metadata or {}
        }
        
        # Update with LLM result if valid
        if llm_result and isinstance(llm_result, dict):
            if 'format' in llm_result and 'intent' in llm_result:
                result.update({
                    'format': llm_result['format'],
                    'intent': llm_result['intent']
                })
                # Preserve any additional metadata from LLM
                if 'metadata' in llm_result and isinstance(llm_result['metadata'], dict):
                    result['metadata'].update(llm_result['metadata'])
        # Detect business intent using comprehensive pattern matching
        intent = None
        confidence = 0.0
        intent_confidence = {}
        
        # Few-shot examples patterns for each intent category
        intent_patterns = {
            'RFQ': ['request for quote', 'price inquiry', 'quotation', 'cost estimate', 'pricing information',
                   'how much would it cost', 'requesting a quote', 'requesting proposal', 'send me a quote'],
            
            'Complaint': ['complaint', 'dissatisfied', 'unhappy', 'problem with', 'issue with', 'not working',
                         'failed to', 'poor service', 'disappointed', 'refund', 'compensation', 'unacceptable',
                         'terrible', 'horrible', 'bad experience', 'frustrated', 'angry'],
            
            'Invoice': ['invoice', 'payment', 'amount due', 'bill', 'receipt', 'charge', 'transaction',
                       'account', 'paid', 'balance', 'due date', 'payment terms', 'subtotal', 'total amount'],
            
            'Regulation': ['compliance', 'regulation', 'law', 'legal', 'gdpr', 'hipaa', 'pci', 'sox', 'policy', 
                          'requirement', 'standard', 'certification', 'audit', 'regulatory', 'compliance report'],
            
            'Fraud Risk': ['fraud', 'suspicious', 'unauthorized', 'unusual activity', 'security breach', 
                          'identity theft', 'scam', 'phishing', 'compromised', 'hack', 'malicious',
                          'investigation', 'dispute', 'not authorized']
        }
        
        text_lower = text_blob.lower()
        
        # Calculate confidence scores for each intent
        for intent_type, patterns in intent_patterns.items():
            matches = sum(1 for pattern in patterns if pattern in text_lower)
            if matches > 0:
                # Calculate confidence based on number of matches and pattern strength
                confidence_score = min(0.5 + (matches * 0.1), 0.95)  # Cap at 0.95
                intent_confidence[intent_type] = confidence_score
        
        # Select intent with highest confidence
        if intent_confidence:
            intent = max(intent_confidence.items(), key=lambda x: x[1])[0]
            confidence = intent_confidence[intent]
        else:
            intent = 'Unknown'
            confidence = 0.3
            
        # Add confidence data to metadata
        metadata['intent_confidence'] = confidence
        metadata['intent_matches'] = intent_confidence
        # Build readable summary for all formats
        summary = []
        summary.append(f"Format: {format}")
        summary.append(f"Intent: {intent}")
        summary.append("")
        if format == 'Image':
            summary.append("Extracted Text (first 300 chars):")
            summary.append((text_blob[:300] + ("..." if len(text_blob) > 300 else "")) if text_blob else "(No text detected)")
        elif format == 'PDF':
            summary.append("PDF Content (first 300 chars):")
            summary.append((text_blob[:300] + ("..." if len(text_blob) > 300 else "")) if text_blob else "(No text detected)")
        elif format == 'Email':
            summary.append("Email Content (first 300 chars):")
            summary.append((text_blob[:300] + ("..." if len(text_blob) > 300 else "")) if text_blob else "(No text detected)")
        elif format == 'JSON':
            summary.append("JSON Content:")
            summary.append((text_blob[:300] + ("..." if len(text_blob) > 300 else "")) if text_blob else "(No content detected)")
        else:
            summary.append("Content (first 300 chars):")
            summary.append((text_blob[:300] + ("..." if len(text_blob) > 300 else "")) if text_blob else "(No content detected)")
        summary.append("")
        summary.append("Metadata:")
        for k, v in (metadata or {}).items():
            summary.append(f"  - {k}: {v}")
        result = {"format": format, "intent": intent, "metadata": metadata, "text_excerpt": '\n'.join(summary)}
        return result

