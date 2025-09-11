"""
LLM-Driven Tool Orchestrator
Minimal orchestration code - LLM does all the reasoning about tool selection and usage.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from services.llm_service import HuggingFaceInferenceService
from services.tool_registry import tool_registry, ToolResult


class LLMOrchestrator:
    """Orchestrates LLM + Tools with minimal code - LLM makes all decisions"""
    
    def __init__(self, llm_service: HuggingFaceInferenceService):
        self.llm = llm_service
        self.logger = logging.getLogger(__name__)
    
    async def process_request(self, user_request: str, user_language: str = "pt") -> str:
        """
        Process user request using LLM + tools
        
        This is the ONLY method needed - LLM does everything:
        - Understands user intent
        - Decides which tools to use
        - Determines tool parameters
        - Formats final response
        """
        self.logger.info(f"Processing request: {user_request}")
        
        try:
            # Get available tools for LLM
            available_tools = tool_registry.get_tool_definitions()
            
            # Let LLM analyze request and decide on tool usage
            tool_decisions = await self._get_llm_tool_decisions(user_request, available_tools, user_language)
            
            if not tool_decisions.get('success', False):
                return self._create_error_response(tool_decisions.get('error', 'Unknown error'), user_language)
            
            # Execute tools based on LLM decisions
            tool_results = await self._execute_tools(tool_decisions.get('tools_to_use', []))
            
            # Let LLM format final response using tool results
            final_response = await self._get_llm_final_response(
                user_request, 
                tool_decisions, 
                tool_results, 
                user_language
            )
            
            return final_response.get('content', 'I apologize, but I encountered an issue processing your request.')
            
        except Exception as e:
            self.logger.error(f"Error in orchestrator: {e}")
            return self._create_error_response(str(e), user_language)
    
    async def _get_llm_tool_decisions(self, user_request: str, available_tools: List[Dict], user_language: str) -> Dict[str, Any]:
        """Let LLM decide which tools to use and with what parameters"""
        
        tools_description = self._format_tools_for_llm(available_tools)
        current_time = datetime.now().isoformat()
        
        prompt = f"""You are an intelligent personal assistant that helps users with emails and calendar management.

CURRENT CONTEXT:
- Current date/time: {current_time}
- User language preference: {user_language}
- Available tools: You have access to various tools for searching, listing, and creating emails and calendar events

AVAILABLE TOOLS:
{tools_description}

USER REQUEST: "{user_request}"

TASK: Analyze the user's request and determine:
1. What the user wants to accomplish
2. Which tool(s) to use to fulfill their request
3. What parameters to pass to each tool

RESPONSE FORMAT: Return a JSON object with this structure:
{{
  "success": true,
  "user_intent": "brief description of what user wants",
  "reasoning": "explanation of your approach",
  "tools_to_use": [
    {{
      "tool_name": "exact_tool_name",
      "parameters": {{
        "param1": "value1",
        "param2": "value2"
      }},
      "purpose": "why using this tool"
    }}
  ]
}}

IMPORTANT RULES:
1. Only use tools that are available in the list above
2. Match tool parameters exactly to their definitions
3. For date/time parameters, use proper ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
4. For "days_back" parameters, use reasonable values (1-30 days typically)
5. For "max_results" parameters, use reasonable limits (5-20 typically)
6. If user asks for "next event" or "upcoming", use get_upcoming_events with max_results=1
7. If user asks about emails, determine if they want unread (use get_unread_emails) or search (use search_emails)
8. If user wants to create something, use create_email or create_calendar_event tools
9. Always provide parameters that make sense for the user's request

EXAMPLES:
- "How many unread emails?" → use get_unread_emails
- "Find emails from John last week" → use search_emails with appropriate query and days_back
- "What's my next meeting?" → use get_upcoming_events with max_results=1
- "Create meeting tomorrow at 2pm" → use create_calendar_event with proper datetime
- "Send email to john@example.com" → use create_email

Return ONLY the JSON object, no additional text."""

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt="You are a tool selection assistant. Return only valid JSON with tool decisions.",
                temperature=0.1  # Low temperature for consistent JSON
            )
            
            if not response.success:
                return {"success": False, "error": f"LLM error: {response.error}"}
            
            # Parse JSON response
            try:
                decisions = json.loads(response.content.strip())
                self.logger.info(f"LLM tool decisions: {decisions}")
                return decisions
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse LLM JSON response: {e}")
                self.logger.warning(f"Raw response: {response.content}")
                return {"success": False, "error": f"Invalid JSON response from LLM: {e}"}
                
        except Exception as e:
            return {"success": False, "error": f"Error getting LLM decisions: {e}"}
    
    async def _execute_tools(self, tools_to_use: List[Dict]) -> List[Dict[str, Any]]:
        """Execute the tools decided by LLM"""
        results = []
        
        for tool_spec in tools_to_use:
            tool_name = tool_spec.get('tool_name')
            parameters = tool_spec.get('parameters', {})
            purpose = tool_spec.get('purpose', '')
            
            self.logger.info(f"Executing tool: {tool_name} with params: {parameters}")
            
            try:
                result = await tool_registry.execute_tool(tool_name, parameters)
                results.append({
                    'tool_name': tool_name,
                    'parameters': parameters,
                    'purpose': purpose,
                    'success': result.success,
                    'data': result.data,
                    'error': result.error
                })
            except Exception as e:
                self.logger.error(f"Error executing tool {tool_name}: {e}")
                results.append({
                    'tool_name': tool_name,
                    'parameters': parameters,
                    'purpose': purpose,
                    'success': False,
                    'data': None,
                    'error': str(e)
                })
        
        return results
    
    async def _get_llm_final_response(self, user_request: str, tool_decisions: Dict, tool_results: List[Dict], user_language: str) -> Dict[str, Any]:
        """Let LLM format the final response using tool results"""
        
        # Format tool results with enhanced formatting for better presentation
        results_summary = []
        for result in tool_results:
            if result['success']:
                results_summary.append(f"✅ {result['tool_name']}: {result['purpose']} - Success")
                if result['data']:
                    # Apply smart formatting based on tool type
                    formatted_data = self._format_tool_data(result['tool_name'], result['data'])
                    results_summary.append(f"   Data: {formatted_data}")
            else:
                results_summary.append(f"❌ {result['tool_name']}: {result['purpose']} - Failed: {result['error']}")
        
        results_text = "\n".join(results_summary)
        
        prompt = f"""You are a helpful personal assistant. Based on the user's request and the tool execution results, provide a natural, helpful response.

USER REQUEST: "{user_request}"

YOUR PLANNED APPROACH: {tool_decisions.get('reasoning', '')}

TOOL EXECUTION RESULTS:
{results_text}

FORMATTING INSTRUCTIONS:
1. Respond in {user_language} (Portuguese if pt, English if en, etc.)
2. Be natural and conversational
3. Directly address what the user asked for
4. Use **bold formatting** for important titles, names, and subjects
5. Format dates and times clearly (e.g., "📅 11/09/2025 ⏰ 16:00")
6. Use emojis sparingly but effectively for visual enhancement
7. Structure information with bullet points or numbered lists
8. For calendar events: **Event Title** - Date/Time - Location (if any)
9. For emails: **Subject** - From: Sender - Date/Time
10. Keep response concise but complete

FORMATTING EXAMPLES:
- For unread emails: "Você tem 5 emails não lidos:\n• **Assunto importante** - De: João Silva - 📅 10/09 ⏰ 14:30"
- For next event: "Seu próximo evento é:\n**Meeting com John** - 📅 11/09 ⏰ 14:00 - Sala de Reuniões"
- For creating event: "Criei o evento **Meeting com John** para 📅 11/09 ⏰ 14:00"
- For no results: "Não encontrei emails correspondentes à sua pesquisa"

IMPORTANT: Use markdown formatting (**bold**) and emojis to make responses clear and visually appealing!

Provide a helpful, natural response based on the tool results:"""

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=f"You are a helpful assistant. Respond naturally in {user_language}. Be concise but informative.",
                temperature=0.6  # Slightly higher for natural responses
            )
            
            return {"content": response.content if response.success else "I encountered an error processing your request."}
            
        except Exception as e:
            self.logger.error(f"Error getting final response: {e}")
            return {"content": self._create_error_response(str(e), user_language)}
    
    def _format_tool_data(self, tool_name: str, data: Dict) -> str:
        """Format tool data with enhanced presentation"""
        
        if tool_name == 'get_unread_emails':
            emails = data.get('unread_emails', [])
            if not emails:
                return "No unread emails found"
            
            formatted = []
            for email in emails[:10]:  # Limit to 10 for readability
                subject = email.get('subject', 'No Subject')[:60]  # Truncate long subjects
                sender = email.get('from', 'Unknown Sender')
                date = email.get('date', '')
                snippet = email.get('snippet', '')[:100]  # Truncate snippet
                
                formatted.append(f"**{subject}** - De: {sender} - {date}\n   {snippet}")
            
            return f"{len(emails)} emails:\n" + "\n".join(formatted)
        
        elif tool_name == 'search_emails':
            emails = data.get('emails', [])
            if not emails:
                return "No emails found for this search"
            
            formatted = []
            for email in emails[:10]:
                subject = email.get('subject', 'No Subject')[:60]
                sender = email.get('from', 'Unknown Sender')
                date = email.get('date', '')
                snippet = email.get('snippet', '')[:100]
                
                formatted.append(f"**{subject}** - De: {sender} - {date}\n   {snippet}")
            
            return f"{len(emails)} emails found:\n" + "\n".join(formatted)
        
        elif tool_name in ['get_upcoming_events', 'search_calendar_events']:
            events_key = 'upcoming_events' if 'upcoming_events' in data else 'events'
            events = data.get(events_key, [])
            if not events:
                return "No events found"
            
            formatted = []
            for event in events[:10]:
                title = event.get('title', 'No Title')
                start_date = event.get('start_date', '')
                start_time = event.get('start_time', '')
                location = event.get('location', '')
                time_until = event.get('time_until', '')
                
                event_line = f"**{title}**"
                if start_date:
                    event_line += f" - 📅 {start_date}"
                if start_time and start_time != 'All day':
                    event_line += f" ⏰ {start_time}"
                if location:
                    event_line += f" 📍 {location}"
                if time_until:
                    event_line += f" (em {time_until})"
                
                formatted.append(event_line)
            
            return f"{len(events)} events:\n" + "\n".join(formatted)
        
        elif tool_name == 'get_current_time':
            current_time = data.get('current_time', '')
            current_date = data.get('current_date', '')
            current_weekday = data.get('current_weekday', '')
            
            return f"📅 {current_date} ({current_weekday}) ⏰ {current_time}"
        
        # Default formatting for other tools
        return json.dumps(data, default=str, indent=2)
    
    def _format_tools_for_llm(self, tools: List[Dict]) -> str:
        """Format tool definitions for LLM understanding"""
        descriptions = []
        for tool in tools:
            name = tool['name']
            desc = tool['description']
            
            # Format parameters
            params = tool['parameters']['properties']
            required_params = tool['parameters'].get('required', [])
            
            param_list = []
            for param_name, param_info in params.items():
                param_type = param_info['type']
                param_desc = param_info['description']
                is_required = param_name in required_params
                req_marker = " (required)" if is_required else " (optional)"
                param_list.append(f"  - {param_name} ({param_type}){req_marker}: {param_desc}")
            
            param_str = "\n".join(param_list) if param_list else "  No parameters"
            
            descriptions.append(f"{name}: {desc}\nParameters:\n{param_str}\n")
        
        return "\n".join(descriptions)
    
    def _create_error_response(self, error: str, language: str) -> str:
        """Create error response in appropriate language"""
        if language.startswith('pt'):
            return f"Desculpe, encontrei um problema ao processar seu pedido: {error}"
        else:
            return f"I apologize, but I encountered an issue: {error}"