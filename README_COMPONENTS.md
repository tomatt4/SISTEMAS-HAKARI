# 🎉 Components V2 - Sistema de Embeds do HAKARI Bot

## ✨ O que foi feito?

Todas as **embeds do bot foram adaptadas** para usar um novo sistema moderno e reutilizável chamado **Components V2**. Isso significa:

- ✅ **Menos repetição de código** - Não precisa criar embed manualmente toda vez
- ✅ **Mais fácil de customizar** - Basta herdar da classe `BaseEmbed`
- ✅ **Cores automáticas** - Cada tipo de embed tem uma cor padrão
- ✅ **Código mais limpo** - Melhor organização e legibilidade
- ✅ **Fácil de manter** - Mudar uma embed afeta todas em um lugar

---

## 📁 Arquivos Modificados

| Arquivo | O que mudou |
|---------|------------|
| `components.py` | ✨ **NOVO** - Sistema completo de embeds |
| `cogs/utilidades.py` | Usa `ServerInfoEmbed`, `UserInfoEmbed`, `PingEmbed`, `HelpEmbed` |
| `cogs/admin.py` | Usa `WarnEmbed`, `ErrorEmbed` |
| `cogs/diversao.py` | Usa `ConfessionEmbed`, `ConfessionLogEmbed` |
| `cogs/ticket.py` | Usa `TicketEmbed`, `TicketOpenedEmbed`, etc |
| `EMBED_GUIDE.md` | 📚 **NOVO** - Guia completo de uso |
| `EXEMPLOS_COMPONENTS.py` | 💡 **NOVO** - 10 exemplos práticos |

---

## 🚀 Como Começar

### 1. Usar uma Embed Pré-Feita

```python
from components import PingEmbed

# Antes (código antigo)
embed = discord.Embed(
    title="🏓 Pong!",
    description=f"Latência: {latency}ms",
    color=discord.Color.green() if latency < 100 else ...
)
await ctx.send(embed=embed)

# Agora (código novo) ✨
embed = PingEmbed(latency).build()
await ctx.send(embed=embed)
```

### 2. Criar uma Embed Customizada

```python
from components import BaseEmbed, EmbedType

class MeuProdutoEmbed(BaseEmbed):
    def __init__(self, nome: str, preco: float):
        super().__init__(
            title=f"🛍️ {nome}",
            embed_type=EmbedType.SUCCESS
        )
        self.add_field("Preço", f"R$ {preco}")

embed = MeuProdutoEmbed("iPhone 15", 5999).build()
await ctx.send(embed=embed)
```

### 3. Usar Encadeamento

```python
embed = BaseEmbed("Título", "Descrição") \
    .add_field("A", "1") \
    .add_field("B", "2") \
    .build()

await ctx.send(embed=embed)
```

---

## 🎯 Principais Classes

### `BaseEmbed` - A Base de Tudo
```python
BaseEmbed(
    title="Título",
    description="Descrição",
    embed_type=EmbedType.SUCCESS,  # SUCCESS, ERROR, INFO, WARNING, NEUTRAL
    color=None,  # Customizar cor (opcional)
    thumbnail_url="...",
    image_url="...",
    footer_text="...",
    author_name="..."
)
```

### Embeds Pré-Feitas
- `ServerInfoEmbed` - Info do servidor
- `UserInfoEmbed` - Info de usuário
- `PingEmbed` - Latência do bot
- `HelpEmbed` - Ajuda
- `WarnEmbed` - Aviso
- `ConfessionEmbed` - Confissão anônima
- `TicketEmbed` - Painel de tickets
- `ErrorEmbed` - Erro genérico
- `SuccessEmbed` - Sucesso genérico

---

## 📊 Exemplo Completo

**ANTES (código antigo):**
```python
embed = discord.Embed(
    title="👤 Informações de João",
    color=discord.Color.blue()
)
embed.set_thumbnail(url=member.display_avatar.url)
embed.add_field("🆔 ID", member.id, inline=False)
embed.add_field("📅 Conta criada", member.created_at.strftime("%d/%m/%Y"), inline=True)
embed.add_field("📥 Entrou no servidor", member.joined_at.strftime("%d/%m/%Y"), inline=True)
embed.add_field("🤖 Bot?", str(member.bot), inline=True)
await ctx.send(embed=embed)
```

**DEPOIS (código novo):**
```python
embed = UserInfoEmbed(member).build()
await ctx.send(embed=embed)
```

💾 **-15 linhas de código!**

---

## 🎨 Cores Automáticas

Cada `EmbedType` tem uma cor padrão:

```python
EmbedType.SUCCESS  → 🟢 Verde
EmbedType.ERROR    → 🔴 Vermelho
EmbedType.INFO     → 🔵 Azul
EmbedType.WARNING  → 🟠 Laranja
EmbedType.NEUTRAL  → ⚫ Cinza
```

Mas você pode customizar:
```python
BaseEmbed("Título", embed_type=EmbedType.SUCCESS, color=discord.Color.red())
```

---

## 📚 Documentação

- **EMBED_GUIDE.md** - Guia completo (recomendado!)
- **EXEMPLOS_COMPONENTS.py** - 10 exemplos práticos
- **components.py** - Código-fonte com comentários

---

## ⚡ Dicas Importantes

✅ **Sempre use `.build()`** antes de enviar:
```python
embed = UserInfoEmbed(member)
await ctx.send(embed=embed.build())  # ✓ Correto
await ctx.send(embed=embed)  # ✗ Errado
```

✅ **Use encadeamento para código limpo:**
```python
# ✓ Bom
embed = BaseEmbed("Título", "Desc") \
    .add_field("A", "1") \
    .add_field("B", "2") \
    .build()

# ✗ Feio
embed = BaseEmbed("Título", "Desc")
embed.add_field("A", "1")
embed.add_field("B", "2")
final = embed.build()
```

---

## 🔧 Para Adicionar Novas Embeds

1. Crie uma classe que herda de `BaseEmbed`
2. Use `super().__init__()` para configurar
3. Adicione campos com `.add_field()`
4. Use `.build()` para enviar

**Exemplo:**
```python
class StatusEmbed(BaseEmbed):
    def __init__(self, status: str, mensagem: str):
        super().__init__(
            title=f"📊 Status",
            description=mensagem,
            embed_type=EmbedType.INFO
        )
        self.add_field("Status", status)

# Usar
embed = StatusEmbed("Online", "Tudo funcionando!").build()
```

---

## 🎓 Próximos Passos

1. Leia **EMBED_GUIDE.md** para entender tudo
2. Veja **EXEMPLOS_COMPONENTS.py** para exemplos práticos
3. Explore o código em **components.py**
4. Crie suas próprias embeds customizadas!

---

## 🐛 Se Algo Quebrar

Se uma embed não funcionar:

1. **Verifique `.build()`** - Você chamou `.build()`?
2. **Verifique imports** - `from components import NomeEmbed`
3. **Verifique sintaxe** - Falta uma vírgula?
4. **Veja o erro** - Discord envia um erro, leia-o!

---

Pronto! Agora seu bot tem um sistema de embeds profissional e reutilizável! 🚀

Qualquer dúvida, veja o guia completo em **EMBED_GUIDE.md**
