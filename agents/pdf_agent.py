# PDFAgent: Extracts fields from PDF, flags conditions

class PDFAgent:
    def __init__(self, memory):
        self.memory = memory

    def process(self, pdf_path):
        """
        Extract invoice or policy fields, flag if invoice > 10k or policy mentions compliance terms.
        """
        from PyPDF2 import PdfReader
        import re
        result = {'fields': {}, 'flags': [], 'action': None}
        try:
            reader = PdfReader(pdf_path)
            text = ''
            for page in reader.pages:
                text += page.extract_text() or ''
            text_lower = text.lower()
            # Invoice extraction
            invoice_total = None
            total_match = re.search(r'total (amount due|due|):?\s*\$?([\d,]+\.?\d*)', text_lower)
            if total_match:
                invoice_total = float(total_match.group(2).replace(',', ''))
                result['fields']['invoice_total'] = invoice_total
                if invoice_total > 10000:
                    result['flags'].append('invoice_total_gt_10000')
            # Policy compliance check
            compliance_terms = ['gdpr', 'fda', 'hipaa', 'pci', 'sox']
            found_terms = [term for term in compliance_terms if term in text_lower]
            if found_terms:
                result['flags'].append(f'policy_mentions: {", ".join(found_terms)}')
            # Action
            if 'invoice_total_gt_10000' in result['flags']:
                result['action'] = 'flag_high_value_invoice'
            elif result['flags']:
                result['action'] = 'flag_compliance_risk'
            else:
                result['action'] = 'store_ok'
            # Improved extraction for readability
            invoice_number = None
            invoice_date = None
            billed_to = None
            subtotal = None
            tax = None
            line_items = []

            # Extract invoice number
            match = re.search(r'invoice\s*#?\s*[:]?\s*(\d+)', text, re.IGNORECASE)
            if match:
                invoice_number = match.group(1)
                result['fields']['invoice_number'] = invoice_number
            # Extract date
            match = re.search(r'date\s*[:]?\s*([\d\-/]+)', text, re.IGNORECASE)
            if match:
                invoice_date = match.group(1)
                result['fields']['invoice_date'] = invoice_date
            # Extract billed to
            match = re.search(r'billed to\s*:?\s*(.+)', text, re.IGNORECASE)
            if match:
                billed_to = match.group(1).split('\n')[0].strip()
                result['fields']['billed_to'] = billed_to
            # Extract subtotal
            match = re.search(r'subtotal\s*\$?([\d,]+\.?\d*)', text, re.IGNORECASE)
            if match:
                subtotal = match.group(1)
                result['fields']['subtotal'] = subtotal
            # Extract tax
            match = re.search(r'tax[\s\(\w\)]*\$?([\d,]+\.?\d*)', text, re.IGNORECASE)
            if match:
                tax = match.group(1)
                result['fields']['tax'] = tax
            # Extract line items (simple heuristic)
            items_section = re.search(r'Description\s+Quantity\s+Unit Price\s+Total\n(.+?)\nSubtotal', text, re.DOTALL)
            if items_section:
                items_lines = items_section.group(1).strip().split('\n')
                for line in items_lines:
                    parts = re.split(r'\s{2,}', line.strip())
                    if len(parts) >= 4:
                        line_items.append({
                            'description': parts[0],
                            'quantity': parts[1],
                            'unit_price': parts[2],
                            'total': parts[3]
                        })
                result['fields']['line_items'] = line_items
            # Build readable summary
            summary = []
            summary.append(f"Invoice Number: {invoice_number or 'N/A'}")
            summary.append(f"Date: {invoice_date or 'N/A'}")
            summary.append(f"Billed To: {billed_to or 'N/A'}")
            summary.append("")
            summary.append("Line Items:")
            if line_items:
                for item in line_items:
                    summary.append(f"  - {item['description']} x{item['quantity']} @ {item['unit_price']} = {item['total']}")
            else:
                summary.append("  (Not detected)")
            summary.append("")
            summary.append(f"Subtotal: {subtotal or 'N/A'}")
            summary.append(f"Tax: {tax or 'N/A'}")
            summary.append(f"Total: {invoice_total or 'N/A'}")
            result['fields']['text_excerpt'] = '\n'.join(summary)

        except Exception as e:
            result['flags'].append(f'pdf_parse_error: {str(e)}')
            result['action'] = 'log_alert'
        return result
