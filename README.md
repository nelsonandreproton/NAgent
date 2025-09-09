# 🤖 Agent Orchestrator

Um orquestrador inteligente de agentes que fornece resumos diários coordenando agentes do Gmail e Google Calendar usando Ollama LLM local (gemma2:2b) com suporte para notificações no Telegram.

## ✨ Funcionalidades

- 📧 **Agente Gmail**: Busca e resume emails não lidos com filtros inteligentes
- 📅 **Agente Calendário**: Analisa reuniões diárias e identifica conflitos
- 🤖 **Integração LLM**: Usa instância local do Ollama com modelo gemma2:2b
- 📱 **Notificações Telegram**: Envia resumos diários diretamente para o seu Telegram
- 🌍 **Multi-idioma**: Suporte para português (PT/BR), inglês, espanhol e outros
- ⏰ **Agendamento Flexível**: Execução sob demanda ou automática diária
- 📊 **Saídas Ricas**: Formatos JSON, texto ou HTML
- 🎨 **Interface CLI**: Interface terminal rica com cores e tabelas
- 🔧 **Configurável**: Sistema extenso de configuração YAML

## 🚀 Início Rápido

### 1. Pré-requisitos

- Python 3.8+
- [Ollama](https://ollama.ai/) instalado e em execução
- Projeto Google Cloud Console com APIs Gmail e Calendar ativadas
- (Opcional) Bot do Telegram configurado

### 2. Instalação

```bash
# Clone ou descarregue o projeto
cd NAgent

# Instale as dependências
pip install -r requirements.txt

# Instale e inicie o Ollama com modelo gemma2:2b
ollama pull gemma2:2b
ollama serve
```

### 3. Configuração Google API

1. Vá para [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto ou selecione um existente
3. Ative a Gmail API e Calendar API
4. Crie credenciais OAuth 2.0 (Aplicação Desktop)
5. Descarregue `credentials.json` e coloque na pasta `credentials/`

### 4. Configuração Telegram (Opcional)

1. Abra o Telegram e procure [@BotFather](https://t.me/BotFather)
2. Envie `/newbot` e siga as instruções
3. Guarde o token do bot (formato: `123456:ABC-DEF1234...`)
4. Obtenha o seu Chat ID:
   - Envie mensagem para [@userinfobot](https://t.me/userinfobot) 
   - Copie o seu ID numérico (ex: `123456789`)
5. Teste o bot enviando-lhe uma mensagem primeiro

### 5. Configuração

```bash
# Copie o template de ambiente
cp .env.template .env

# Edite as configurações
vim .env
```

### 6. Primeiro Teste

```bash
# Verifique o estado do sistema
python main.py --status

# Gere um resumo imediatamente
python main.py --run-now

# Inicie o modo agendado
python main.py --schedule
```

## ⚙️ Configuração

### Variáveis de Ambiente (.env)

```bash
# Google API
GOOGLE_CREDENTIALS_PATH=credentials/credentials.json

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma2:2b

# Telegram (Opcional)
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=123456789

# Agendamento
DAILY_SUMMARY_TIME=09:00
TIMEZONE=UTC

# Saída
OUTPUT_FORMAT=json
SUMMARY_LENGTH=medium
```

### Configuração Principal (config/config.yaml)

O sistema usa um arquivo de configuração YAML com secções para:

- **Schedule**: Horários de resumos automáticos
- **Language**: Configuração de idioma (pt-pt, pt-br, en, es, fr, de, it)
- **Ollama**: Configurações do modelo LLM
- **Google API**: Autenticação e configuração de âmbitos
- **Gmail**: Filtros de email e opções de processamento
- **Calendar**: Seleção de eventos e categorização
- **Telegram**: Configuração de notificações
- **Summary**: Formato de saída e níveis de detalhe
- **Logging**: Níveis de log e saída de arquivo

#### Configuração de Idioma

```yaml
language:
  # Idioma padrão para resumos (pt-pt, pt-br, en, es, fr, de, it)
  default: "pt-pt"
  # Formato de data para o idioma selecionado
  date_format: "%d/%m/%Y"
  # Formato de hora para o idioma selecionado  
  time_format: "%H:%M"
```

#### Configuração Telegram

```yaml
telegram:
  # Enviar resumo diário automaticamente
  send_daily_summary: true
  # Enviar notificações de erro
  send_error_notifications: true
  # Enviar atualizações de estado do sistema
  send_status_updates: false
  # Formato da mensagem (html, markdown, text)
  message_format: "html"
```

## 📱 Usar com Telegram

### Configuração Rápida

1. **Criar Bot**: Fale com @BotFather → `/newbot`
2. **Obter Chat ID**: Fale com @userinfobot
3. **Configurar .env**:
   ```bash
   TELEGRAM_ENABLED=true
   TELEGRAM_BOT_TOKEN=seu_token_aqui
   TELEGRAM_CHAT_ID=seu_chat_id_aqui
   ```
4. **Testar**: `python main.py --run-now`

### Tipos de Notificações

- 📋 **Resumos Diários**: Emails e reuniões formatados
- ⚠️ **Notificações de Erro**: Quando algo falha
- 🔍 **Estado do Sistema**: Verificações de conectividade
- ⏰ **Execuções Agendadas**: Início/fim de tarefas automáticas

### Exemplo de Mensagem Telegram

```
🤖 Resumo Diário - Agent Orchestrator
📅 15/01/2024

📧 Emails não lidos: 12
📩 Recentes (3h): 3

📅 Reuniões hoje: 4
💻 Virtuais: 2
⏰ Duração total: 3.5h

📋 Resumo do Dia:
[Resumo inteligente gerado pelo LLM]

Gerado às 09:00
```

## 🌍 Suporte Multi-idioma

### Idiomas Disponíveis

- **pt-pt**: Português de Portugal (padrão)
- **pt-br**: Português do Brasil
- **en**: Inglês
- **es**: Espanhol
- **fr**: Francês
- **de**: Alemão
- **it**: Italiano

### Como Alterar o Idioma

Edite `config/config.yaml`:
```yaml
language:
  default: "en"  # Para inglês
```

O idioma afeta:
- Mensagens do Telegram
- Formatos de data/hora
- Notificações do sistema
- Interface CLI

## 💻 Exemplos de Uso

### Interface de Linha de Comando

```bash
# Verificação de estado do sistema
python main.py --status

# Geração imediata de resumo
python main.py --run-now

# Modo agendado (executa diariamente na hora configurada)
python main.py --schedule

# Modo debug com logging verboso
python main.py --run-now --debug

# Usar arquivo de configuração personalizado
python main.py --config minha-config.yaml --run-now
```

### Uso Programático

```python
from main import AgentOrchestrator

# Inicializar orquestrador
orchestrator = AgentOrchestrator("config/config.yaml")

# Verificar estado do sistema
status = orchestrator.check_system_status()

# Gerar resumo diário
summary = orchestrator.generate_daily_summary()

# Exibir no terminal
orchestrator.display_summary(summary)
```

## 📊 Formatos de Saída

### Formato JSON
```json
{
  "timestamp": "2024-01-15T09:00:00",
  "email_summary": "Tem 12 emails não lidos...",
  "calendar_summary": "Tem 4 reuniões hoje...",
  "unified_summary": "Resumo Diário: Aqui está o seu dia...",
  "statistics": {
    "email": {"total_unread": 12, "recent_count": 3},
    "calendar": {"total_events": 4, "virtual_meetings": 2}
  }
}
```

### Formato Texto
Resumo unificado em texto simples, perfeito para notificações.

### Formato HTML  
Saída HTML rica com estilos, perfeita para relatórios de email ou dashboards web.

## 🏗️ Arquitetura

```
Agent Orchestrator
├── main.py                    # Orquestrador principal e CLI
├── services/
│   ├── google_auth.py         # Gestão OAuth 2.0 Google
│   ├── llm_service.py         # Cliente Ollama LLM
│   ├── telegram_service.py    # Integração bot Telegram
│   └── translations.py       # Serviço de traduções
├── agents/
│   ├── gmail_agent.py         # Integração Gmail API
│   └── calendar_agent.py      # Integração Calendar API
├── config/
│   └── config.yaml           # Configuração principal
├── credentials/              # Credenciais Google API
├── summaries/               # Arquivos de resumos gerados
└── logs/                    # Logs da aplicação
```

### Detalhes dos Componentes

#### Agente Gmail
- Busca emails não lidos com filtros configuráveis
- Extrai remetente, assunto e preview de conteúdo
- Agrupa emails por remetente e tópico
- Identifica emails urgentes/importantes
- Fornece resumos de recurso se LLM não disponível

#### Agente Calendário  
- Obtém eventos do calendário de hoje
- Categoriza reuniões (virtual, presencial, tipos)
- Calcula duração e identifica conflitos
- Extrai informações de participantes e local
- Fornece sugestões de optimização de agenda

#### Serviço Ollama
- Liga à instância local do Ollama
- Suporta prompts e templates personalizados
- Gere configuração de temperatura e tokens
- Fornece tratamento de erros e recursos
- Optimizado para modelo gemma2:2b

#### Gestor de Autenticação
- Gere fluxo OAuth 2.0 automaticamente
- Gere atualização e armazenamento de tokens
- Fornece utilitários de teste de ligação
- Suporta revogação de credenciais

## 🔧 Configurações Avançadas

### Filtros de Email
```yaml
gmail:
  labels: ["IMPORTANT", "CATEGORY_PERSONAL"]
  exclude_senders: ["noreply@example.com"]
  max_age_hours: 24
```

### Personalização Calendário
```yaml
calendar:
  include_all_day: true
  min_duration_minutes: 15
  days_ahead: 1
```

### Personalização LLM
```yaml
ollama:
  temperature: 0.7
  max_tokens: 1000
  timeout: 30
```

### Execução Agendada
```yaml
schedule:
  enabled: true
  daily_time: "08:30"
  timezone: "Europe/Lisbon"
```

## 🔍 Resolução de Problemas

### Problemas Comuns

**Falha de Ligação Ollama**
```bash
# Verificar se Ollama está em execução
curl http://localhost:11434/api/tags

# Iniciar Ollama se necessário
ollama serve

# Instalar modelo se em falta
ollama pull gemma2:2b
```

**Erros de Autenticação Google**
```bash
# Verificar se arquivo de credenciais existe
ls -la credentials/credentials.json

# Remover tokens em cache para re-autenticar
rm credentials/token.json

# Verificar quotas de API no Google Cloud Console
```

**Problemas Telegram**
```bash
# Verificar se bot token e chat ID estão corretos
# Certificar-se de que enviou mensagem para o bot primeiro
# Testar ligação manual:
curl -X POST "https://api.telegram.org/botSEU_TOKEN/sendMessage" \
     -H "Content-Type: application/json" \
     -d '{"chat_id": "SEU_CHAT_ID", "text": "teste"}'
```

**Erros de Permissão**
```bash
# Certificar-se de que main.py é executável
chmod +x main.py

# Verificar permissões de pasta
chmod 755 credentials/ config/ logs/
```

### Modo Debug

Ativar logging abrangente:
```bash
python main.py --run-now --debug
```

Isto fornece informações detalhadas sobre:
- Chamadas e respostas de API
- Fluxo de autenticação
- Processo de geração LLM
- Stack traces de erros

### Verificação Estado Sistema

Comece sempre a resolução de problemas com:
```bash
python main.py --status
```

Isto verifica:
- ✅ Disponibilidade Ollama e acesso a modelo
- ✅ Estado de autenticação Google API
- ✅ Conectividade Gmail e Calendar API
- ✅ Ligação Telegram Bot
- ✅ Validade da configuração

## 🔐 Notas de Segurança

- Credenciais são armazenadas localmente e nunca transmitidas
- Tokens OAuth são encriptados e auto-renovados
- Chamadas API usam bibliotecas cliente oficial Google
- Processamento LLM acontece inteiramente local (via Ollama)
- Dados sensíveis são excluídos dos logs
- Nunca commita ficheiros .env ou credentials para repositórios públicos

## 🤝 Contribuir

1. Faça fork do repositório
2. Crie um branch de funcionalidade
3. Faça as suas alterações
4. Adicione testes se aplicável  
5. Atualize a documentação
6. Submeta um pull request

## 📄 Licença

Licença MIT - veja arquivo LICENSE para detalhes.

## 🆘 Suporte

Para questões e problemas:
1. Verifique a secção de resolução de problemas acima
2. Reveja logs em `logs/orchestrator.log`
3. Execute verificação de estado do sistema
4. Consulte `TELEGRAM_SETUP_PT.md` para configuração Telegram
5. Crie uma issue com detalhes do sistema e logs

## 📈 Roadmap

- [ ] Suporte para múltiplos calendários
- [ ] Integração com mais LLMs (OpenAI, Claude, etc.)
- [ ] Interface web dashboard
- [ ] Plugins para outros serviços (Slack, Discord, etc.)
- [ ] Análise de sentimento de emails
- [ ] Sugestões inteligentes de resposta

---

**Agent Orchestrator** - Simplifique a sua rotina diária com inteligência artificial! 🚀