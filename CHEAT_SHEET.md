# 📋 Cheat Sheet - Components V2

## ⚡ Uso Rápido

### Embed Simples
```python
from components import BaseEmbed, EmbedType

embed = BaseEmbed(
    title="Título",
    description="Descrição",
    embed_type=EmbedType.SUCCESS
).build()

await ctx.send(embed=embed)
```

### Com Campos
```python
embed = BaseEmbed("Título", "Desc") \
    .add_field("Campo 1", "Valor 1") \
    .add_field("Campo 2", "Valor 2") \
    .build()

await ctx.send(embed=embed)
```

### Embeds Pré-Feitas
```python
# Info do servidor
from components import ServerInfoEmbed
embed = ServerInfoEmbed(ctx.guild).build()

# Info de usuário
from components import UserInfoEmbed
embed = UserInfoEmbed(member).build()

# Ping
from components import PingEmbed
embed = PingEmbed(latency_ms).build()

# Ajuda
from components import HelpEmbed
embed = HelpEmbed(bot_name, prefix, commands_text).build()

# Aviso
from components import WarnEmbed
embed = WarnEmbed(member, reason, moderator).build()

# Confissão
from components import ConfessionEmbed, ConfessionLogEmbed
embed1 = ConfessionEmbed(texto).build()
embed2 = ConfessionLogEmbed(texto, user, guild).build()

# Tickets
from components import TicketEmbed, TicketOpenedEmbed
from components import ConfirmCloseTicketEmbed, TicketClosedEmbed

# Genéricas
from components import ErrorEmbed, SuccessEmbed
embed = ErrorEmbed("Erro", "Mensagem").build()
embed = SuccessEmbed("Sucesso", "Mensagem").build()
```

---

## 🎨 Tipos de Embed

```python
EmbedType.SUCCESS   # Verde - Sucesso
EmbedType.ERROR     # Vermelho - Erro
EmbedType.INFO      # Azul - Informação
EmbedType.WARNING   # Laranja - Aviso
EmbedType.NEUTRAL   # Cinza - Neutro
```

---

## 🎯 Opções do BaseEmbed

```python
BaseEmbed(
    title="...",                    # Título
    description="...",              # Descrição principal
    embed_type=EmbedType.INFO,      # Tipo (define cor)
    color=discord.Color.red(),      # Cor customizada (opcional)
    thumbnail_url="...",            # Imagem pequena
    image_url="...",                # Imagem grande
    footer_text="...",              # Texto do rodapé
    footer_icon="...",              # Ícone do rodapé
    author_name="...",              # Nome do autor
    author_icon="..."               # Ícone do autor
)
```

---

## 🔗 Encadeamento

```python
# ✅ BOAS PRÁTICAS
embed = BaseEmbed("Título", "Desc") \
    .add_field("A", "1", inline=True) \
    .add_field("B", "2", inline=False) \
    .build()

# ✅ Mais limpo com múltiplas linhas
embed = BaseEmbed("Título", "Desc")
embed.add_field("A", "1")
embed.add_field("B", "2")
final_embed = embed.build()
```

---

## 💾 Criar Embed Customizada

```python
from components import BaseEmbed, EmbedType

class MeuEmbed(BaseEmbed):
    def __init__(self, param1, param2):
        super().__init__(
            title="Meu Título",
            embed_type=EmbedType.SUCCESS
        )
        self.add_field("Campo", param1)
        self.add_field("Outro", param2)

# Usar
embed = MeuEmbed("valor1", "valor2").build()
```

---

## ⚠️ Erros Comuns

| Erro | Solução |
|------|---------|
| `AttributeError: 'BaseEmbed' object has no attribute 'build'` | Você esqueceu de chamar `.build()` |
| `ModuleNotFoundError: No module named 'components'` | Falta `from components import ...` |
| Embed não aparece | Verifique se `.build()` foi chamado |
| Cor errada | Especifique `color=discord.Color.xxx` |

---

## 🎓 Lembrar

1. **Sempre `.build()`** antes de enviar
2. **Sempre importe** do `components`
3. **Encadeie** com `\` para código limpo
4. **Tipos definem cores** automaticamente
5. **Customize** herdando da classe

---

## 🚀 Pronto para Usar!

Agora é só usar nos seus comandos! 🎉

Dúvidas? Veja:
- `EMBED_GUIDE.md` - Guia completo
- `EXEMPLOS_COMPONENTS.py` - 10 exemplos práticos
- `components.py` - Código-fonte
