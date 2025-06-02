# EmailAgent: Extracts fields, tone, urgency, triggers action
import re
import json
import os
import random
from datetime import datetime

class EmailAgent:
    def __init__(self, memory=None):
        self.memory = memory
        
        # Define patterns for tone detection
        self.tone_patterns = {
            'angry': ['furious', 'angry', 'outraged', 'frustrated', 'annoyed', 'terrible service', 
                    'disappointed', 'unacceptable', 'worst', 'complaint', 'demanding', 'upset',
                    'unprofessional', 'never again', 'escalate', 'incompetent', '!!', '???'],
            
            'threatening': ['lawyer', 'legal action', 'lawsuit', 'sue', 'court', 'legal team', 'attorney',
                          'consequences', 'demand', 'immediately', 'or else', 'ultimatum', 'deadline',
                          'compensation', 'media', 'public', 'expose', 'escalate to', 'regulatory'],
            
            'urgent': ['urgent', 'immediately', 'asap', 'emergency', 'critical', 'time-sensitive',
                     'deadline', 'urgent matter', 'promptly', 'without delay', 'as soon as possible',
                     'pressing', 'high priority', 'expedite', 'now', 'today'],
            
            'polite': ['please', 'thank you', 'appreciate', 'grateful', 'kindly', 'regards', 'sincerely',
                     'respectfully', 'consideration', 'understanding', 'assistance', 'help', 'support',
                     'sorry to bother', 'at your convenience', 'when possible']
        }
        
    def detect_tone(self, text):
        """Analyze email text to detect tone based on keyword patterns"""
        text_lower = text.lower()
        tone_scores = {}
        
        # Calculate scores for each tone based on keyword matches
        for tone, patterns in self.tone_patterns.items():
            matches = sum(1 for pattern in patterns if pattern.lower() in text_lower)
            if matches > 0:
                # More matches = higher confidence in the tone
                tone_scores[tone] = min(0.4 + (matches * 0.1), 0.95)  # Cap at 0.95
        
        # Determine primary tone (highest score)
        if tone_scores:
            primary_tone = max(tone_scores.items(), key=lambda x: x[1])[0]
            confidence = tone_scores[primary_tone]
        else:
            # Default to neutral if no strong indicators
            primary_tone = 'neutral'
            confidence = 0.6
            tone_scores['neutral'] = confidence
            
        return {
            'primary_tone': primary_tone,
            'confidence': confidence,
            'tone_scores': tone_scores
        }
        
    def process(self, email_content):
        """Extract structured information from email content"""
        # This handles both raw email content or file path to email
        if os.path.isfile(email_content):
            try:
                with open(email_content, 'r', encoding='utf-8') as f:
                    email_text = f.read()
            except Exception as e:
                return {
                    "status": "error",
                    "format": "Email",
                    "error": f"Failed to read email file: {str(e)}",
                    "fields": {"error": str(e), "text_excerpt": f"Error: {str(e)}"}
                }
        else:
            email_text = email_content
        
        fields = {}
        
        # Extract basic email components (simplified)
        sender_match = re.search(r'From:\s*([^\n]+)', email_text, re.IGNORECASE)
        subject_match = re.search(r'Subject:\s*([^\n]+)', email_text, re.IGNORECASE)
        to_match = re.search(r'To:\s*([^\n]+)', email_text, re.IGNORECASE)
        date_match = re.search(r'Date:\s*([^\n]+)', email_text, re.IGNORECASE)
        
        fields['sender'] = sender_match.group(1).strip() if sender_match else 'Unknown'
        fields['subject'] = subject_match.group(1).strip() if subject_match else 'No Subject'
        fields['recipient'] = to_match.group(1).strip() if to_match else 'Unknown'
        fields['date'] = date_match.group(1).strip() if date_match else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Extract email body (everything after headers)
        body_match = re.search(r'\n\n(.+)', email_text, re.DOTALL)
        body = body_match.group(1).strip() if body_match else email_text
        fields['body'] = body
        
        # Identify issue/request from subject and first paragraph
        first_para = body.split('\n\n')[0] if '\n\n' in body else body
        fields['issue'] = fields['subject']
        fields['request'] = first_para[:200] + ('...' if len(first_para) > 200 else '')
        
        # Analyze tone
        tone_analysis = self.detect_tone(body)
        fields['tone'] = tone_analysis['primary_tone']
        fields['tone_confidence'] = tone_analysis['confidence']
        fields['tone_details'] = tone_analysis['tone_scores']
        
        # Identify urgency based on keywords and tone
        if 'urgent' in tone_analysis['tone_scores'] and tone_analysis['tone_scores']['urgent'] > 0.6:
            fields['urgency'] = 'high'
        elif 'angry' in tone_analysis['tone_scores'] and tone_analysis['tone_scores']['angry'] > 0.7:
            fields['urgency'] = 'high'
        elif 'threatening' in tone_analysis['tone_scores'] and tone_analysis['tone_scores']['threatening'] > 0.5:
            fields['urgency'] = 'critical'
        else:
            fields['urgency'] = 'normal'
        
        # Determine suggested action based on tone and urgency
        action = self.determine_action(fields)
        
        # Create a tracking number for follow-up
        tracking_id = f"EMAIL-{random.randint(10000, 99999)}"
        fields['tracking_id'] = tracking_id
        
        # Build readable summary
        summary = []
        summary.append(f"Sender: {fields['sender']}")
        summary.append(f"Subject: {fields['subject']}")
        summary.append(f"Urgency: {fields['urgency']}")
        summary.append(f"Tone: {fields['tone']} (confidence: {fields['tone_confidence']:.2f})")
        summary.append(f"Action: {action['action']} ({action['priority']} priority)")
        summary.append("")
        summary.append("Email Body (first 300 chars):")
        summary.append(body[:300] + ("..." if len(body) > 300 else ""))
        
        fields['text_excerpt'] = '\n'.join(summary)
        
        return {
            "status": "processed",
            "format": "Email",
            "fields": fields,
            "summary": f"Email from {fields['sender']} with subject: {fields['subject']}",
            "suggested_action": action,
            "tracking_id": tracking_id
        }
    
    def determine_action(self, fields):
        """Determine appropriate action based on email tone and urgency"""
        # Get tone and urgency
        tone = fields.get('tone', 'neutral')
        urgency = fields.get('urgency', 'normal')
        
        # Define actions based on tone+urgency combinations
        if tone == 'threatening' or urgency == 'critical':
            return {
                "action": "escalate",
                "target": "crm",
                "priority": "critical",
                "details": f"Escalate to legal/management immediately - {fields.get('subject', 'No subject')}",
                "endpoint": "/crm/escalate"
            }
        elif tone == 'angry' and urgency == 'high':
            return {
                "action": "escalate",
                "target": "crm",
                "priority": "high",
                "details": f"Customer is upset - {fields.get('subject', 'No subject')}",
                "endpoint": "/crm/escalate"
            }
        elif urgency == 'high':
            return {
                "action": "flag",
                "target": "support",
                "priority": "high",
                "details": f"Urgent issue - {fields.get('subject', 'No subject')}",
                "endpoint": "/support/create_ticket"
            }
        elif tone == 'polite' and urgency == 'normal':
            return {
                "action": "log",
                "target": "crm",
                "priority": "normal",
                "details": f"Routine request - {fields.get('subject', 'No subject')}",
                "endpoint": "/crm/log_communication"
            }
        else:
            return {
                "action": "log",
                "target": "system",
                "priority": "low",
                "details": f"Standard message - {fields.get('subject', 'No subject')}",
                "endpoint": "/system/log"
            }
