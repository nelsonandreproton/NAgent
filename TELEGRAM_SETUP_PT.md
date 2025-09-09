# 📱 Guia de Configuração do Bot Telegram

Este guia explica como configurar um bot do Telegram para receber os resumos diários do Agent Orchestrator.

## 📋 Pré-requisitos

- Conta do Telegram ativa
- Aplicação do Telegram instalada (móvel ou desktop)
- Agent Orchestrator já configurado e funcionando

## 🤖 Passo 1: Criar o Bot no Telegram

### 1.1 Contactar o BotFather
1. Abra o Telegram
2. Procure por **@BotFather** ou aceda a [t.me/BotFather](https://t.me/BotFather)
3. Inicie uma conversa clicando em **"Iniciar"**

### 1.2 Criar o Novo Bot
1. Envie o comando: `/newbot`
2. O BotFather irá pedir o nome do bot:
   ```
   Alright, a new bot. How are we going to call it? Please choose a name for your bot.
   ```
3. Escreva um nome descritivo (ex: `Agent Orchestrator Bot`)

4. O BotFather irá pedir o username do bot:
   ```
   Good. Now let's choose a username for your bot. It must end in 'bot'. Like this, for example: TetrisBot or tetris_bot.
   ```
5. Escreva um username único que termine em "bot" (ex: `MeuAgentOrchestrator_bot`)

### 1.3 Guardar o Token
Após criar o bot, receberá uma mensagem com o token:
```
Done! Congratulations on your new bot. You will find it at t.me/MeuAgentOrchestrator_bot. 
You can now add a description, about section and profile picture for your bot.

Use this token to access the HTTP API:
123456789:ABCDEF1234567890abcdef1234567890ABC

Keep your token secure and store it safely, it can be used by anyone to control your bot.
```

**⚠️ IMPORTANTE**: Copie e guarde este token num local seguro!

## 🆔 Passo 2: Obter o seu Chat ID

### 2.1 Método Automático (Recomendado)
1. Procure por **@userinfobot** no Telegram
2. Inicie uma conversa
3. O bot irá mostrar imediatamente as suas informações:
   ```
   👤 Nome: Seu Nome
   🆔 ID: 123456789
   👤 Username: @seu_username
   ```
4. Copie o número do **ID** (ex: `123456789`)

### 2.2 Método Manual (Alternativo)
1. Inicie uma conversa com o seu bot (procure pelo username que criou)
2. Envie qualquer mensagem para o bot (ex: "Olá")
3. Abra o seguinte URL no browser (substitua `SEU_TOKEN` pelo token do bot):
   ```
   https://api.telegram.org/botSEU_TOKEN/getUpdates
   ```
4. Procure pelo seu `chat_id` na resposta JSON

## ⚙️ Passo 3: Configurar o Agent Orchestrator

### 3.1 Editar o ficheiro .env
Abra o ficheiro `.env` no diretório do Agent Orchestrator:

```bash
# Telegram Configuration
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=123456789:ABCDEF1234567890abcdef1234567890ABC
TELEGRAM_CHAT_ID=123456789
```

### 3.2 Configurar o config.yaml (Opcional)
Para configurações avançadas, edite `config/config.yaml`:

```yaml
telegram:
  # Ativar notificações do Telegram
  enabled: true
  # Token do bot (será sobreposto pela variável de ambiente)
  bot_token: ""
  # ID do chat (será sobreposto pela variável de ambiente)
  chat_id: ""
  # Enviar resumo diário automaticamente
  send_daily_summary: true
  # Enviar notificações de erro
  send_error_notifications: true
  # Enviar atualizações do estado do sistema
  send_status_updates: false
```

## ✅ Passo 4: Testar a Configuração

### 4.1 Verificar o Estado do Sistema
Execute o comando:
```bash
python main.py --status
```

Deverá ver o Telegram como "✅ Connected" na tabela de status.

### 4.2 Testar Envio Manual
Para testar se o bot funciona, execute:
```bash
python main.py --run-now
```

Se tudo estiver configurado corretamente, receberá uma mensagem no Telegram com o resumo.

## 🔧 Resolução de Problemas

### ❌ "Bot token invalid"
- Verifique se copiou o token completamente
- Certifique-se de que não há espaços extras
- O token deve ter o formato: `123456789:ABC...`

### ❌ "Chat not found" ou "Forbidden"
- Verifique se o Chat ID está correto
- **IMPORTANTE**: Deve enviar pelo menos uma mensagem para o bot primeiro
- Inicie uma conversa com o bot antes de testar

### ❌ "Telegram not configured"
- Certifique-se de que `TELEGRAM_ENABLED=true` no ficheiro .env
- Verifique se tanto `TELEGRAM_BOT_TOKEN` como `TELEGRAM_CHAT_ID` estão definidos

### ❌ Bot não responde
- Confirme que o bot está ativo (procure-o no Telegram)
- Teste manualmente enviando uma mensagem para o bot
- Use o comando `/status` dentro do chat com o bot

## 📱 Personalizar as Notificações

### Tipos de Notificações Disponíveis:
1. **Resumo Diário**: Enviado automaticamente ou sob demanda
2. **Notificações de Erro**: Quando algo falha no sistema
3. **Estado do Sistema**: Verificações de conectividade
4. **Execuções Agendadas**: Início e conclusão das tarefas automáticas

### Configurar Notificações:
Edite o `config/config.yaml`:

```yaml
telegram:
  send_daily_summary: true        # Resumos diários
  send_error_notifications: true  # Erros do sistema
  send_status_updates: false      # Updates de estado
```

## 🔐 Segurança

- **Nunca partilhe o token do bot** - qualquer pessoa com acesso pode controlar o bot
- Mantenha o ficheiro `.env` seguro e não o commite para repositórios públicos
- Considere usar um bot dedicado apenas para o Agent Orchestrator
- Se suspeitar que o token foi comprometido, crie um novo bot

## 📝 Exemplo de Mensagem Recebida

Quando funcionar corretamente, receberá mensagens formatadas como esta:

```
🤖 Resumo Diário - Agent Orchestrator
📅 2024-01-15

📧 Emails não lidos: 12
📩 Recentes (3h): 3

📅 Reuniões hoje: 4
💻 Virtuais: 2
⏰ Duração total: 3.5h

📋 Resumo do Dia:
Daily Briefing: Here's your day at a glance...

[Resumo detalhado gerado pelo LLM]

Gerado às 09:00
```

## 🆘 Suporte

Se continuar com problemas:
1. Verifique os logs em `logs/orchestrator.log`
2. Execute `python main.py --debug --status` para informações detalhadas
3. Teste a conectividade manualmente com as APIs do Telegram
4. Consulte a documentação oficial do Telegram Bot API