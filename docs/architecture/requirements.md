# Requisitos do sistema

## 1. Objetivo

Documentar os requisitos funcionais e não funcionais do SPHEREx Explorer.

Os requisitos orientam o desenvolvimento, os testes e a avaliação do MVP.

## 2. Requisitos funcionais

### RF-001 — Informar coordenadas

O sistema deverá permitir que o usuário informe Ascensão Reta (RA) e Declinação (Dec).

### RF-002 — Validar coordenadas

O sistema deverá verificar se as coordenadas estão dentro dos intervalos válidos.

Para coordenadas em graus:

- RA: 0° a menos de 360°.
- Dec: -90° a +90°.

### RF-003 — Selecionar campo de visão

O usuário deverá poder selecionar o campo de visão da pesquisa.

Os valores disponíveis deverão respeitar as limitações do arquivo científico e da aplicação.

### RF-004 — Consultar observações

O backend deverá consultar o arquivo científico SPHEREx para os parâmetros recebidos.

### RF-005 — Identificar observações

O sistema deverá apresentar as observações disponíveis e seus identificadores.

### RF-006 — Organizar observações temporalmente

O sistema deverá organizar as observações por data de observação.

### RF-007 — Exibir imagens

O sistema deverá apresentar imagens processadas adequadas à visualização no navegador.

### RF-008 — Reproduzir sequência

O sistema deverá permitir a reprodução sequencial das observações disponíveis.

### RF-009 — Pausar reprodução

O usuário deverá conseguir interromper a reprodução.

### RF-010 — Navegar entre observações

O usuário deverá conseguir avançar e retroceder manualmente.

### RF-011 — Exibir metadados

O sistema deverá apresentar informações relevantes da observação selecionada.

### RF-012 — Informar ausência de resultados

O sistema deverá informar claramente quando nenhuma observação for encontrada.

### RF-013 — Tratar falhas

O sistema deverá apresentar mensagens apropriadas quando houver falhas de consulta, recuperação ou processamento.

## 3. Requisitos não funcionais

### RNF-001 — Correção científica

As informações apresentadas deverão ter origem identificável e ser compatíveis com os metadados disponíveis.

### RNF-002 — Desempenho

O sistema deverá evitar downloads desnecessários de arquivos científicos grandes.

### RNF-003 — Usabilidade

A interface deverá permitir que usuários sem conhecimento técnico especializado realizem uma pesquisa básica.

### RNF-004 — Responsividade

A interface deverá se adaptar a diferentes tamanhos de tela.

### RNF-005 — Manutenibilidade

O código deverá ser organizado em módulos com responsabilidades definidas.

### RNF-006 — Segurança

Parâmetros e recursos externos deverão ser validados.

### RNF-007 — Rastreabilidade

As observações deverão manter referências aos produtos científicos originais.

### RNF-008 — Tratamento de erros

Falhas externas e internas deverão ser tratadas sem encerrar indevidamente a aplicação.

### RNF-009 — Integridade dos dados

O processamento não deverá modificar os arquivos científicos originais.

### RNF-010 — Transparência

Limitações, dados ausentes e incompatibilidades deverão ser informados ao usuário quando relevantes.

## 4. Requisitos científicos específicos

### RC-001 — Diferenciar banda e época

O sistema deverá distinguir bandas espectrais de épocas de observação.

### RC-002 — Preservar metadados temporais

O sistema deverá manter a referência temporal original das observações.

### RC-003 — Considerar movimento próprio

A pesquisa deverá considerar o movimento próprio de objetos quando isso for relevante para localizar corretamente o alvo.

### RC-004 — Identificar incompatibilidades

O sistema deverá preservar informações sobre diferenças de banda, detector e qualidade.

### RC-005 — Não inventar dados

Campos ausentes não poderão ser preenchidos com valores fictícios apresentados como reais.

## 5. Critérios de aceitação do MVP

O MVP será considerado funcional quando:

1. O usuário conseguir informar coordenadas válidas.
2. O usuário conseguir selecionar um campo de visão permitido.
3. O backend conseguir realizar uma consulta real.
4. A aplicação conseguir identificar observações disponíveis.
5. As observações forem organizadas cronologicamente.
6. Pelo menos uma imagem real puder ser recuperada e exibida.
7. O usuário conseguir navegar entre observações.
8. A aplicação apresentar metadados relevantes.
9. A ausência de resultados e falhas forem tratadas.
10. A demonstração estiver documentada e reproduzível.

A quantidade e a diversidade de observações necessárias para validar a sequência temporal deverão ser definidas após a investigação científica.

## 6. Requisitos fora do MVP inicial

- Detecção automática de novos objetos.
- Subtração avançada de imagens.
- Análise espectral completa.
- Integração obrigatória com Gaia.
- Banco de dados de usuários.
- Autenticação.
- Histórico persistente de pesquisas.
- Infraestrutura distribuída.

Esses recursos poderão ser avaliados posteriormente.

## 7. Prioridade

| Prioridade | Requisitos |
|---|---|
| Essencial | RF-001 a RF-013 |
| Essencial | RNF-001, RNF-002, RNF-003, RNF-005, RNF-006, RNF-007 e RNF-008 |
| Essencial | RC-001 a RC-005 |
| Evolução | Comparação, subtração e exploração espectral |

## 8. Responsáveis

**Liderança técnica:** Integrante 1.

**Liderança científica:** Integrante 2.

**Liderança de interface:** Integrante 3.

A validação dos requisitos será compartilhada pela equipe.