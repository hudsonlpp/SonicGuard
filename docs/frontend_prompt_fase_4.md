# Prompt para o Agente Frontend: Integração Fase 4 (Autenticação e Limites)

Copie e cole a mensagem abaixo para o agente do Frontend iniciar os trabalhos da nova fase:

***

**Contexto:**
O Backend do SonicGuard concluiu a Fase 4 (Monetização e Autenticação) e adicionou proteções de concorrência ao motor DSP pesado. O motor agora processa apenas 1 música por vez globalmente no servidor para evitar quebras de memória na nuvem (usando um Semaphore).

Sua tarefa agora é conectar o nosso frontend React/Vite ao novo sistema de contas e preparar a UX para a fila de espera.

**Instruções:**
1. **Leia o Contrato da API:** Consulte o recém-atualizado `docs/api_contract.md` para entender as novas rotas `/api/auth/register` e `/api/auth/login`.
2. **Crie o Sistema de Login/Cadastro:** 
   - Crie as telas/modais de Login e Registro. 
   - Capture o Token JWT do login e persista ele com segurança (ex: `localStorage` ou cookies).
3. **Proteja a Chamada Principal:**
   - Na função que chama o `POST /api/compare`, adicione o header `Authorization: Bearer <token_jwt>`.
4. **Tratamento de Erros e Paywall:**
   - Se a API retornar **Status 401**, o token expirou. Deslogue o usuário e o mande para a tela de Login.
   - Se a API retornar **Status 402**, o usuário está sem "Créditos" (moedas). Exiba um Modal amigável dizendo "Seus créditos acabaram! Deseja fazer um Upgrade?".
5. **Ajuste Crítico de Timeout e UX (Loading):**
   - Como o Backend agora usa um *Semaphore* (fila de 1 por 1), a resposta do `/api/compare` não vai mais demorar invariavelmente 40s. Se houver 3 pessoas testando músicas ao mesmo tempo, a do nosso usuário pode demorar *2 minutos* aguardando na fila. 
   - Aumente o *timeout* do `fetch` ou do `axios` no frontend para pelo menos **3 a 5 minutos**.
   - Melhore o texto da tela de Loading (Dica: após 30 segundos, mude a mensagem de "Processando o Áudio" para "Você está na fila e o servidor está gerando a matriz DTW. Isso pode levar alguns instantes...").
