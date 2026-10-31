# Recursos de terceros

| Recurso | Procedencia | Licencia incluida |
|---|---|---|
| DM Sans, variable Latin | [Fontsource](https://fontsource.org/fonts/dm-sans) | `armario/static/fonts/OFL-DM-Sans.txt` |
| DM Serif Display, Latin 400 | [Fontsource](https://fontsource.org/fonts/dm-serif-display) | `armario/static/fonts/OFL-DM-Serif-Display.txt` |

Ambas fuentes se redistribuyen con sus avisos SIL Open Font License 1.1 y se sirven localmente. Los paquetes de ejecución mantienen sus licencias propias; `requirements.txt` fija sus versiones.

El símbolo de la aplicación, los iconos SVG y las ilustraciones de demostración se han creado para este proyecto. Las prendas de demo se dibujan desde `armario/demo.py`. Las capturas documentales se generan con ese inventario ficticio.

## Modelos opcionales, sin redistribución de pesos

La integración local admite [Qwen3-VL 4B Instruct Q4](https://ollama.com/library/qwen3-vl:4b-instruct-q4_K_M) y [Qwen3 4B Instruct 2507 Q4](https://ollama.com/library/qwen3:4b-instruct-2507-q4_K_M), cuyas fichas publican licencia Apache 2.0. Los modelos y [Ollama](https://github.com/ollama/ollama) se instalan aparte; el repositorio no distribuye sus pesos ni cambia su licencia. Revisa sus avisos vigentes antes de redistribuirlos. [LOCAL_AI.md](LOCAL_AI.md) recoge configuración y límites de la integración.
