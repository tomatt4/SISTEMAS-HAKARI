# 📚 Guia Completo: Components V2 - Sistema de Embeds do Bot

## 🎯 O que são Components V2?

Components V2 é um sistema de embeds **reutilizável, modular e fácil de customizar** para o Discord. Basicamente, em vez de criar embeds manualmente toda vez, temos classes prontas que fazem tudo por você!

---

## 📦 Estrutura Básica

O arquivo `components.py` contém:

### 1. **Classe Base: `BaseEmbed`**
É como um "template" para criar embeds. Todas as outras embeds herdam dela.

```python
from components import BaseEmbed, EmbedType

# Criar uma embed simples
embed = BaseEmbed(
    title="Meu Título",
    description="Minha descrição",
    embed_type=EmbedType.SUCCESS  # Define cor automaticamente
)

# Adicionar campos (permite encadeamento)
embed.add_field("Campo 1", "Valor 1").add_field("Campo 2", "Valor 2")

# Construir e enviar
final_embed = embed.build()
await ctx.send(embed=final_embed)
```

---

## 🎨 Tipos de Embed (EmbedType)

| Tipo | Cor | Uso |
|------|-----|-----|
| `SUCCESS` | 🟢 Verde | Operações bem-sucedidas |
| `ERROR` | 🔴 Vermelho | Erros e problemas |
| `INFO` | 🔵 Azul | Informações gerais |
| `WARNING` | 🟠 Laranja | Avisos e confirmações |
| `NEUTRAL` | ⚫ Cinza | Mensagens neutras |

---

## 💡 Embeds Pré-Feitas do Bot

### 1️⃣ **ServerInfoEmbed** - Informações do Servidor
```python
from components import ServerInfoEmbed

embed = ServerInfoEmbed(ctx.guild).build()
await ctx.send(embed=embed)
```

**Mostra:**
- Nome do servidor
- Dono
- Quantidade de membros
- Boosts
- Data de criação

---

### 2️⃣ **UserInfoEmbed** - Informações de Usuário
```python
from components import UserInfoEmbed

member = await ctx.guild.fetch_member(123456789)
embed = UserInfoEmbed(member).build()
await ctx.send(embed=embed)
```

**Mostra:**
- Nome/Avatar do usuário
- ID
- Data de criação da conta
- Quando entrou no servidor
- Se é bot ou não

---

### 3️⃣ **PingEmbed** - Latência da API
```python
from components import PingEmbed

latency = round(bot.latency * 1000)  # ms
embed = PingEmbed(latency).build()
await ctx.send(embed=embed)
```

**Automático:**
- Cor muda conforme a latência (verde < 100ms, amarelo < 200ms, vermelho > 200ms)

---

### 4️⃣ **HelpEmbed** - Ajuda e Comandos
```python
from components import HelpEmbed

embed = HelpEmbed(
    bot_name="HAKARI",
    prefix=",",
    commands_text="Lista de comandos aqui..."
).build()
await ctx.send(embed=embed)
```

---

### 5️⃣ **WarnEmbed** - Aviso de Usuário
```python
from components import WarnEmbed

embed = WarnEmbed(
    member=target_user,
    reason="Spam no chat",
    moderator=ctx.author
).build()
await ctx.send(embed=embed)
```

---

### 6️⃣ **ConfessionEmbed** & **ConfessionLogEmbed** - Confissões
```python
from components import ConfessionEmbed, ConfessionLogEmbed

# Confissão pública (anônima)
embed1 = ConfessionEmbed(texto_confissao).build()
await canal_publico.send(embed=embed1)

# Log privado (com quem enviou)
embed2 = ConfessionLogEmbed(texto_confissao, user, guild).build()
await canal_logs.send(embed=embed2)
```

---

### 7️⃣ **TicketEmbed** - Painel de Tickets
```python
from components import TicketEmbed

embed = TicketEmbed(image_url="https://...").build()
await ctx.send(embed=embed, view=TicketView())
```

---

### 8️⃣ **ErrorEmbed & SuccessEmbed** - Genéricas
```python
from components import ErrorEmbed, SuccessEmbed

# Erro
embed = ErrorEmbed("❌ Ops!", "Algo deu errado").build()

# Sucesso
embed = SuccessEmbed("✅ Pronto!", "Operação concluída").build()
```

---

## 🛠️ Como Mexer e Customizar

### Criar uma Embed Personalizada

```python
from components import BaseEmbed, EmbedType
import discord

class MeuProductEmbed(BaseEmbed):
    def __init__(self, nome: str, preco: float, estoque: int):
        super().__init__(
            title=f"🛍️ {nome}",
            description="Informações do produto",
            embed_type=EmbedType.SUCCESS,  # Cor verde
            thumbnail_url="https://..."  # Imagem pequena
        )
        
        # Adicionar campos customizados
        self.add_field("💰 Preço", f"R$ {preco}", inline=True)
        self.add_field("📦 Em Estoque", f"{estoque} unidades", inline=True)
        self.add_field("⭐ Avaliação", "4.5/5 ⭐", inline=False)

# Usar
embed = MeuProductEmbed("iPhone 15", 5999.99, 15).build()
await ctx.send(embed=embed)
```

---

### Modificar Cores

```python
from components import BaseEmbed
import discord

# Cor customizada
embed = BaseEmbed(
    title="Meu Título",
    color=discord.Color.from_rgb(255, 0, 255)  # Magenta
)
```

---

### Adicionar Imagens

```python
from components import BaseEmbed

embed = BaseEmbed(
    title="Galeria",
    thumbnail_url="https://... (imagem pequena)",
    image_url="https://... (imagem grande)"
)
```

---

### Encadeamento de Campos

```python
embed = BaseEmbed("Título", "Descrição")
embed.add_field("A", "1") \
     .add_field("B", "2") \
     .add_field("C", "3", inline=False)

final = embed.build()
```

---

## 🔄 Como Funciona Internamente

### 1. **Inicialização**
```
BaseEmbed.__init__() 
  → Define título, descrição, cor
  → Define tipo (SUCCESS, ERROR, etc)
```

### 2. **Adição de Campos**
```
add_field("Nome", "Valor")
  → Cria um objeto EmbedField
  → Armazena na lista self.fields
  → Retorna self (para encadeamento)
```

### 3. **Build (Construção)**
```
embed.build()
  → Cria uma discord.Embed real
  → Adiciona todos os campos
  → Configura cores, footer, timestamp
  → Retorna pronta para enviar
```

---

## 📋 Exemplo Completo

```python
import discord
from discord.ext import commands
from components import BaseEmbed, EmbedType, UserInfoEmbed

class MyCommands(commands.Cog):
    @commands.command()
    async def mycommand(self, ctx):
        # Jeito antigo (sem Components V2)
        # embed = discord.Embed(title="...", color=discord.Color.blue())
        # embed.add_field(...)
        
        # Jeito novo (com Components V2) ✨
        embed = BaseEmbed(
            title="📊 Estatísticas",
            description="Aqui estão suas stats",
            embed_type=EmbedType.INFO
        )
        
        embed.add_field("🎮 Nível", "42", inline=True)
        embed.add_field("⭐ Pontos", "9999", inline=True)
        embed.add_field("📈 Taxa de Vitória", "75%", inline=True)
        
        await ctx.send(embed=embed.build())

    @commands.command()
    async def userprofile(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        
        # Usar embed pré-feita
        embed = UserInfoEmbed(member).build()
        await ctx.send(embed=embed)
```

---

## ⚡ Dicas Importantes

✅ **Sempre use `.build()`** antes de enviar:
```python
embed = BaseEmbed("Título", "Desc")
# CORRETO ✓
await ctx.send(embed=embed.build())

# ERRADO ✗
await ctx.send(embed=embed)
```

✅ **Use encadeamento para código limpo:**
```python
embed = BaseEmbed("Título", "Desc") \
    .add_field("A", "1") \
    .add_field("B", "2")
```

✅ **Tipos de Embed definem cores automaticamente:**
```python
# Sem especificar cor (usa cor automática do tipo)
BaseEmbed("Título", embed_type=EmbedType.SUCCESS)

# Com cor customizada (sobrescreve o tipo)
BaseEmbed("Título", embed_type=EmbedType.SUCCESS, color=discord.Color.red())
```

✅ **Sempre trate erros:**
```python
try:
    await ctx.send(embed=embed.build())
except discord.Forbidden:
    await ctx.send("Sem permissão para enviar embed!")
```

---

## 🎓 Resumo Final

| Conceito | O que é |
|----------|--------|
| **BaseEmbed** | Classe base para criar embeds customizadas |
| **EmbedType** | Enum com tipos predefinidos (SUCCESS, ERROR, etc) |
| **add_field()** | Adiciona campos à embed |
| **build()** | Constrói a embed.Embed final |
| **Encadeamento** | Chamar vários .add_field() seguidos |

Pronto! Agora você pode criar embeds profissionais e reutilizáveis sem esforço! 🚀
