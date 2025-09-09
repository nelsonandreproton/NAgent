"""
Translation Service
Provides multilingual support for Agent Orchestrator summaries and notifications.
"""

from typing import Dict, Any
import logging


class TranslationService:
    """Service for handling translations and localization"""
    
    def __init__(self, language: str = "pt-pt"):
        self.language = language.lower()
        self.logger = logging.getLogger(__name__)
        
        # Load translations
        self.translations = self._load_translations()
        
        # Validate language
        if self.language not in self.translations:
            self.logger.warning(f"Language '{language}' not supported, falling back to pt-pt")
            self.language = "pt-pt"
    
    def _load_translations(self) -> Dict[str, Dict[str, str]]:
        """Load all translations"""
        return {
            "pt-pt": {
                # Headers and titles
                "daily_summary_title": "🤖 Resumo Diário - Agent Orchestrator",
                "email_summary_title": "📧 Resumo de Emails",
                "calendar_summary_title": "📅 Resumo do Calendário",
                "unified_summary_title": "📋 Resumo do Dia",
                "system_status_title": "🔍 Estado do Sistema",
                "error_notification_title": "❌ Agent Orchestrator - Erro",
                
                # Email statistics
                "unread_emails": "Emails não lidos",
                "recent_emails": "Recentes (3h)",
                "no_emails": "Nenhum email não lido encontrado.",
                
                # Calendar statistics  
                "meetings_today": "Reuniões hoje",
                "virtual_meetings": "Virtuais",
                "total_duration": "Duração total",
                "no_meetings": "Nenhuma reunião agendada para hoje.",
                
                # Time and date
                "generated_at": "Gerado às",
                "on_date": "em",
                "hours": "h",
                "minutes": "m",
                
                # System status
                "available": "Disponível",
                "unavailable": "Indisponível", 
                "connected": "Ligado",
                "disconnected": "Desligado",
                "accessible": "Acessível",
                "not_accessible": "Não Acessível",
                "authenticated": "Autenticado",
                "not_authenticated": "Não Autenticado",
                
                # Notifications
                "scheduled_run_started": "Execução Agendada",
                "scheduled_run_started_msg": "A iniciar geração automática do resumo diário...",
                "scheduled_run_completed": "Resumo Concluído",
                "scheduled_run_completed_msg": "Geração automática do resumo diário foi concluída com sucesso!",
                "test_connection": "Agent Orchestrator - Teste de ligação",
                
                # Errors and warnings
                "warnings": "Avisos",
                "errors": "Erros",
                "connection_test": "Verificação",
                
                # Days of week
                "monday": "Segunda-feira",
                "tuesday": "Terça-feira", 
                "wednesday": "Quarta-feira",
                "thursday": "Quinta-feira",
                "friday": "Sexta-feira",
                "saturday": "Sábado",
                "sunday": "Domingo"
            },
            
            "pt-br": {
                # Headers and titles
                "daily_summary_title": "🤖 Resumo Diário - Agent Orchestrator",
                "email_summary_title": "📧 Resumo de E-mails",
                "calendar_summary_title": "📅 Resumo do Calendário",
                "unified_summary_title": "📋 Resumo do Dia",
                "system_status_title": "🔍 Status do Sistema",
                "error_notification_title": "❌ Agent Orchestrator - Erro",
                
                # Email statistics
                "unread_emails": "E-mails não lidos",
                "recent_emails": "Recentes (3h)",
                "no_emails": "Nenhum e-mail não lido encontrado.",
                
                # Calendar statistics
                "meetings_today": "Reuniões hoje",
                "virtual_meetings": "Virtuais",
                "total_duration": "Duração total",
                "no_meetings": "Nenhuma reunião agendada para hoje.",
                
                # Time and date
                "generated_at": "Gerado às",
                "on_date": "em",
                "hours": "h",
                "minutes": "min",
                
                # System status
                "available": "Disponível",
                "unavailable": "Indisponível",
                "connected": "Conectado", 
                "disconnected": "Desconectado",
                "accessible": "Acessível",
                "not_accessible": "Não Acessível",
                "authenticated": "Autenticado",
                "not_authenticated": "Não Autenticado",
                
                # Notifications
                "scheduled_run_started": "Execução Agendada",
                "scheduled_run_started_msg": "Iniciando geração automática do resumo diário...",
                "scheduled_run_completed": "Resumo Concluído",
                "scheduled_run_completed_msg": "Geração automática do resumo diário foi concluída com sucesso!",
                "test_connection": "Agent Orchestrator - Teste de conexão",
                
                # Errors and warnings
                "warnings": "Avisos",
                "errors": "Erros", 
                "connection_test": "Verificação",
                
                # Days of week
                "monday": "Segunda-feira",
                "tuesday": "Terça-feira",
                "wednesday": "Quarta-feira", 
                "thursday": "Quinta-feira",
                "friday": "Sexta-feira",
                "saturday": "Sábado",
                "sunday": "Domingo"
            },
            
            "en": {
                # Headers and titles
                "daily_summary_title": "🤖 Daily Summary - Agent Orchestrator",
                "email_summary_title": "📧 Email Summary",
                "calendar_summary_title": "📅 Calendar Summary",
                "unified_summary_title": "📋 Daily Briefing",
                "system_status_title": "🔍 System Status",
                "error_notification_title": "❌ Agent Orchestrator - Error",
                
                # Email statistics
                "unread_emails": "Unread emails",
                "recent_emails": "Recent (3h)",
                "no_emails": "No unread emails found.",
                
                # Calendar statistics
                "meetings_today": "Meetings today",
                "virtual_meetings": "Virtual",
                "total_duration": "Total duration", 
                "no_meetings": "No meetings scheduled for today.",
                
                # Time and date
                "generated_at": "Generated at",
                "on_date": "on",
                "hours": "h",
                "minutes": "m",
                
                # System status
                "available": "Available",
                "unavailable": "Unavailable",
                "connected": "Connected",
                "disconnected": "Disconnected", 
                "accessible": "Accessible",
                "not_accessible": "Not Accessible",
                "authenticated": "Authenticated",
                "not_authenticated": "Not Authenticated",
                
                # Notifications
                "scheduled_run_started": "Scheduled Execution",
                "scheduled_run_started_msg": "Starting automatic daily summary generation...",
                "scheduled_run_completed": "Summary Completed",
                "scheduled_run_completed_msg": "Automatic daily summary generation completed successfully!",
                "test_connection": "Agent Orchestrator - Connection test",
                
                # Errors and warnings
                "warnings": "Warnings",
                "errors": "Errors",
                "connection_test": "Check",
                
                # Days of week
                "monday": "Monday",
                "tuesday": "Tuesday",
                "wednesday": "Wednesday",
                "thursday": "Thursday", 
                "friday": "Friday",
                "saturday": "Saturday",
                "sunday": "Sunday"
            },
            
            "es": {
                # Headers and titles
                "daily_summary_title": "🤖 Resumen Diario - Agent Orchestrator",
                "email_summary_title": "📧 Resumen de Correos",
                "calendar_summary_title": "📅 Resumen del Calendario",
                "unified_summary_title": "📋 Resumen del Día",
                "system_status_title": "🔍 Estado del Sistema",
                "error_notification_title": "❌ Agent Orchestrator - Error",
                
                # Email statistics
                "unread_emails": "Correos no leídos",
                "recent_emails": "Recientes (3h)",
                "no_emails": "No se encontraron correos no leídos.",
                
                # Calendar statistics
                "meetings_today": "Reuniones hoy",
                "virtual_meetings": "Virtuales",
                "total_duration": "Duración total",
                "no_meetings": "No hay reuniones programadas para hoy.",
                
                # Time and date
                "generated_at": "Generado a las",
                "on_date": "el",
                "hours": "h",
                "minutes": "m",
                
                # System status
                "available": "Disponible",
                "unavailable": "No Disponible",
                "connected": "Conectado",
                "disconnected": "Desconectado",
                "accessible": "Accesible", 
                "not_accessible": "No Accesible",
                "authenticated": "Autenticado",
                "not_authenticated": "No Autenticado",
                
                # Notifications
                "scheduled_run_started": "Ejecución Programada",
                "scheduled_run_started_msg": "Iniciando generación automática del resumen diario...",
                "scheduled_run_completed": "Resumen Completado", 
                "scheduled_run_completed_msg": "¡Generación automática del resumen diario completada con éxito!",
                "test_connection": "Agent Orchestrator - Prueba de conexión",
                
                # Errors and warnings
                "warnings": "Advertencias",
                "errors": "Errores",
                "connection_test": "Verificación",
                
                # Days of week
                "monday": "Lunes",
                "tuesday": "Martes",
                "wednesday": "Miércoles",
                "thursday": "Jueves",
                "friday": "Viernes",
                "saturday": "Sábado",
                "sunday": "Domingo"
            }
        }
    
    def get(self, key: str, **kwargs) -> str:
        """Get translated string with optional formatting"""
        try:
            translation = self.translations[self.language].get(key, key)
            
            # Apply formatting if kwargs provided
            if kwargs:
                translation = translation.format(**kwargs)
                
            return translation
        except Exception as e:
            self.logger.warning(f"Translation error for key '{key}': {e}")
            return key
    
    def format_date(self, date_obj, date_format: str = None) -> str:
        """Format date according to language settings"""
        if not date_format:
            # Use default format from translations or fallback
            date_format = "%d/%m/%Y" if self.language.startswith("pt") else "%Y-%m-%d"
        
        try:
            return date_obj.strftime(date_format)
        except Exception as e:
            self.logger.warning(f"Date formatting error: {e}")
            return str(date_obj)
    
    def format_time(self, time_obj, time_format: str = None) -> str:
        """Format time according to language settings"""
        if not time_format:
            time_format = "%H:%M"
        
        try:
            return time_obj.strftime(time_format)
        except Exception as e:
            self.logger.warning(f"Time formatting error: {e}")
            return str(time_obj)
    
    def get_available_languages(self) -> list:
        """Get list of available languages"""
        return list(self.translations.keys())
    
    def set_language(self, language: str):
        """Change current language"""
        if language.lower() in self.translations:
            self.language = language.lower()
            self.logger.info(f"Language changed to: {self.language}")
        else:
            self.logger.warning(f"Language '{language}' not supported")
    
    def get_current_language(self) -> str:
        """Get current language"""
        return self.language