# SonicGuard — Visão de Produto

## O que é
Ferramenta que **detecta plágio musical** e **orienta juridicamente** com base na Lei 9.610/98 (Lei de Direitos Autorais brasileira).

## Arquitetura do Produto

```
USUÁRIO: "Acho que plagiaram minha música"
        ↓
   ┌─────────────────────────┐
   │  🔊 MOTOR DE DETECÇÃO   │  ✅ PRONTO (DSP v2)
   │  Score + Breakdown       │
   └──────────┬──────────────┘
              ↓
   ┌─────────────────────────┐
   │  ⚖️ MÓDULO JURÍDICO     │  ❌ A CONSTRUIR
   │  Lei 9.610/98           │
   └──────────┬──────────────┘
              ↓
   RELATÓRIO com score, breakdown e orientação legal
```

## Status dos Componentes

| Componente | Status | Função |
|---|---|---|
| Motor DSP v2 | ✅ Pronto | Score + breakdown (melodia, harmonia, ritmo, timbre) |
| API FastAPI | ❌ Falta | Endpoint HTTP para o frontend |
| Módulo Jurídico | ❌ Falta | Scores → artigos da Lei 9.610/98 |
| Frontend | ❌ Falta | UI de upload + resultado + orientação |
| Auth + Pagamento | ❌ Falta | Login, planos, cobrança |

## Modelo de Monetização

| Plano | Preço | Inclui |
|---|---|---|
| Grátis | R$0 | 3 comparações/mês, score geral |
| Pro | R$29-49/mês | Ilimitado, breakdown, orientação jurídica |
| Empresarial | R$99-199/mês | API, relatórios PDF, suporte, selo |

**Público-alvo**: compositores, produtores, gravadoras pequenas, advogados de direito autoral.

## Mapeamento Jurídico (Lei 9.610/98)

- **Score ≥ 85%** → Possível violação (Art. 7º, VIII). Recomendar advogado para ação de cessação + indenização (Art. 102-110).
- **Score 45-85%** → Zona cinzenta. Pode ser inspiração ou obra derivada (Art. 5º, VIII, g). Recomendar perícia.
- **Score < 45%** → Similaridade normal do gênero. Sem indícios.

## Roadmap

1. **API FastAPI** — motor como serviço HTTP
2. **Módulo Jurídico** — scores → orientações legais
3. **Frontend** — UI de upload + resultado visual
4. **Auth + Pagamento** — login + Stripe/Pix
5. **IA Híbrida** — resolver interpolação com mudança de tom

## Cobertura de Detecção (Motor DSP v2)

| Padrão de plágio | Detecção | Mecanismo |
|---|---|---|
| ✅ Sample direto | 85%+ | Sample Rule (harmonia+ritmo) |
| ✅ Cópia vocal | 85%+ | Vocal Rule (melodia) |
| ✅ Cópia de vibe | 65%+ | Vibe Rule (timbre+ritmo) |
| ❌ Interpolação + mudança de tom | ~19% | Limite DSP → resolver com IA híbrida |

## Custos Estimados (Infra)

| Item | BRL/mês |
|---|---|
| VPS sem GPU (Railway) | R$40-145 |
| IA híbrida (baixo volume) | R$15-150 |
| Motor DSP puro | R$0 |
