import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from typing import Optional

# ID do canal onde o painel será enviado
PAINEL_CHANNEL_ID = 1454971586758180907

# Arquivo para armazenar dados das calls
CALLS_DATA_FILE = "calls_data.json"

def load_calls_data():
    """Carrega dados das calls do arquivo JSON"""
    if os.path.exists(CALLS_DATA_FILE):
        with open(CALLS_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_calls_data(data):
    """Salva dados das calls no arquivo JSON"""
    with open(CALLS_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

class NomeCallModal(discord.ui.Modal, title="configurar nome da call"):
    """Modal para configurar o nome da call"""
    nome = discord.ui.TextInput(
        label="nome da call",
        placeholder="digite o novo nome (deixe em branco para padrão)",
        required=False,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        calls_data = load_calls_data()
        voice_channel_id = str(interaction.user.id)
        
        if voice_channel_id not in calls_data:
            await interaction.followup.send("❌ você não possui uma call ativa!", ephemeral=True)
            return
        
        novo_nome = self.nome.value.strip() if self.nome.value else f"Call de {interaction.user.name}"
        
        try:
            channel = interaction.guild.get_channel(int(calls_data[voice_channel_id]["channel_id"]))
            if channel:
                await channel.edit(name=novo_nome)
                calls_data[voice_channel_id]["nome"] = novo_nome
                save_calls_data(calls_data)
                await interaction.followup.send(f"✅ nome da call alterado para: **{novo_nome}**", ephemeral=True)
            else:
                await interaction.followup.send("❌ canal da call não encontrado!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ erro ao alterar nome: {str(e)}", ephemeral=True)

class LimiteCallModal(discord.ui.Modal, title="Configurar Limite de Pessoas"):
    """Modal para configurar o limite de pessoas na call"""
    limite = discord.ui.TextInput(
        label="Limite de Pessoas",
        placeholder="Digite o número (deixe em branco para sem limite)",
        required=False,
        max_length=3
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        calls_data = load_calls_data()
        voice_channel_id = str(interaction.user.id)
        
        if voice_channel_id not in calls_data:
            await interaction.followup.send("❌ você não possui uma call ativa!", ephemeral=True)
            return
        
        try:
            limite_texto = self.limite.value.strip() if self.limite.value else "0"
            limite = int(limite_texto) if limite_texto else 0
            
            if limite < 0:
                await interaction.followup.send("❌ o limite não pode ser negativo!", ephemeral=True)
                return
            
            channel = interaction.guild.get_channel(int(calls_data[voice_channel_id]["channel_id"]))
            if channel:
                await channel.edit(user_limit=limite)
                calls_data[voice_channel_id]["limite"] = limite
                save_calls_data(calls_data)
                
                limite_texto = "sem limite" if limite == 0 else f"{limite} pessoa(s)"
                await interaction.followup.send(f"✅ limite da call definido para: **{limite_texto}**", ephemeral=True)
            else:
                await interaction.followup.send("❌ canal da call não encontrado!", ephemeral=True)
        except ValueError:
            await interaction.followup.send("❌ digite um número válido!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ erro ao alterar limite: {str(e)}", ephemeral=True)

class ConfigCallView(discord.ui.View):
    """View com os botões de configuração da call"""
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(label="Nome", style=discord.ButtonStyle.blurple, custom_id="config_nome")
    async def nome_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.show_modal(NomeCallModal())
    
    @discord.ui.button(label="Limite", style=discord.ButtonStyle.blurple, custom_id="config_limite")
    async def limite_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.show_modal(LimiteCallModal())
    
    @discord.ui.button(label="Pública", style=discord.ButtonStyle.green, custom_id="config_publica")
    async def publica_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        calls_data = load_calls_data()
        voice_channel_id = str(interaction.user.id)
        
        if voice_channel_id not in calls_data:
            await interaction.followup.send("❌ você não possui uma call ativa!", ephemeral=True)
            return
        
        try:
            channel = interaction.guild.get_channel(int(calls_data[voice_channel_id]["channel_id"]))
            if not channel:
                await interaction.followup.send("❌ canal da call não encontrado!", ephemeral=True)
                return
            
            is_public = calls_data[voice_channel_id].get("publica", True)
            novo_status = not is_public
            
            if novo_status:  # Tornando pública
                # Define permissões para pública (qualquer um pode entrar)
                # Remove permissões específicas e volta ao padrão
                for target in list(channel.overwrites.keys()):
                    if target != interaction.guild.default_role:
                        await channel.delete_permissions(target)
                await channel.delete_permissions(interaction.guild.default_role)
                button.style = discord.ButtonStyle.green
                button.label = "Pública"
                status_texto = "🟢 Pública"
            else:  # Tornando privada
                # Define permissões para privada (apenas o criador pode entrar)
                # Nega acesso para @everyone
                overwrite_everyone = discord.PermissionOverwrite(connect=False)
                await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite_everyone)
                # Permite acesso apenas para o criador
                overwrite_owner = discord.PermissionOverwrite(connect=True)
                await channel.set_permissions(interaction.user, overwrite=overwrite_owner)
                button.style = discord.ButtonStyle.red
                button.label = "Privada"
                status_texto = "🔴 Privada"
            
            calls_data[voice_channel_id]["publica"] = novo_status
            save_calls_data(calls_data)
            
            await interaction.followup.send(f"✅ call definida como **{status_texto}**", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ erro ao alterar privacidade: {str(e)}", ephemeral=True)

class CriarCallView(discord.ui.View):
    """View com o botão de criar call"""
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(label="Criar Call", style=discord.ButtonStyle.green, custom_id="criar_call_btn")
    async def criar_call_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        try:
            calls_data = load_calls_data()
            user_id = str(interaction.user.id)
            
            # Verifica se o usuário já possui uma call
            if user_id in calls_data:
                channel = interaction.guild.get_channel(int(calls_data[user_id]["channel_id"]))
                if channel:
                    await interaction.followup.send("❌ tu ja tem uma call abestado, delete ela com /deletarcall", ephemeral=True)
                    return
                else:
                    del calls_data[user_id]
            
            # Cria o canal de voz
            nome_padrao = f"Call de {interaction.user.name}"
            voice_channel = await interaction.guild.create_voice_channel(
                nome_padrao,
                category=None
            )
            
            # Salva os dados da call
            calls_data[user_id] = {
                "channel_id": voice_channel.id,
                "nome": nome_padrao,
                "limite": 0,
                "publica": True,
                "criador": interaction.user.id
            }
            save_calls_data(calls_data)
            
            await interaction.followup.send(
                f"✅ call criada com sucesso!\n**{nome_padrao}**\n\nUse `/configcall` para gerenciar sua call.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"❌ erro ao criar call: {str(e)}", ephemeral=True)

class Calls(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Evento disparado quando o bot está pronto"""
        self.bot.add_view(CriarCallView(self.bot))
        self.bot.add_view(ConfigCallView(self.bot))
        print("✅ Cog de Calls carregada com sucesso!")
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Monitora alterações no estado de voz para deletar calls vazias (opcional)"""
        calls_data = load_calls_data()
        
        # Se o membro saiu de um canal
        if before.channel and not after.channel:
            # Verifica se a call está vazia e se pertence a um usuário
            for user_id, call_info in list(calls_data.items()):
                try:
                    channel = self.bot.get_channel(int(call_info["channel_id"]))
                    if channel and len(channel.members) == 0 and channel.id == before.channel.id:
                        # Call vazia - você pode deletar automaticamente ou deixar como está
                        # Por padrão, vou deixar como está para o usuário deletar manualmente
                        pass
                except:
                    pass
    
    @app_commands.command(name="painelcall", description="Envia o painel de criação de calls (apenas admins)")
    @app_commands.checks.has_permissions(administrator=True)
    async def painelcall(self, interaction: discord.Interaction):
        """Comando para enviar o painel de criar calls no canal especificado"""
        try:
            channel = interaction.client.get_channel(PAINEL_CHANNEL_ID)
            if not channel:
                await interaction.response.send_message("❌ canal do painel não encontrado!", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🎙️ Sistema de Calls Personalizado",
                description="Clique no botão abaixo para criar sua call personalizada!",
                color=discord.Color.blurple()
            )
            embed.add_field(
                name="O que você pode fazer?",
                value="✅ criar uma call com seu nome\n✅ renomear sua call\n✅ definir limite de pessoas\n✅ deixar privada ou pública",
                inline=False
            )
            embed.set_footer(text="Apenas você pode gerenciar sua call!")
            
            await channel.send(embed=embed, view=CriarCallView(self.bot))
            await interaction.response.send_message("✅ painel enviado com sucesso!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ erro ao enviar painel: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="configcall", description="Gerencia sua call personalizada")
    async def configcall(self, interaction: discord.Interaction):
        """Comando para gerenciar a call do usuário"""
        try:
            calls_data = load_calls_data()
            user_id = str(interaction.user.id)
            
            if user_id not in calls_data:
                await interaction.response.send_message("❌ você não possui uma call ativa!", ephemeral=True)
                return
            
            call_info = calls_data[user_id]
            channel = interaction.guild.get_channel(int(call_info["channel_id"]))
            
            if not channel:
                del calls_data[user_id]
                save_calls_data(calls_data)
                await interaction.response.send_message("❌ sua call foi deletada!", ephemeral=True)
                return
            
            # Cria a embed com as informações da call
            embed = discord.Embed(
                title="⚙️ Configurar Call",
                description=f"Canal: **{call_info['nome']}**",
                color=discord.Color.blurple()
            )
            
            limite_texto = "sem limite" if call_info["limite"] == 0 else f"{call_info['limite']} pessoa(s)"
            status_publica = "🟢 Pública" if call_info["publica"] else "🔴 Privada"
            
            embed.add_field(name="Limite", value=limite_texto, inline=True)
            embed.add_field(name="Status", value=status_publica, inline=True)
            
            # Cria a view com os botões
            view = ConfigCallView(self.bot)
            
            # Atualiza o estilo do botão de privacidade se necessário
            for item in view.children:
                if item.custom_id == "config_publica":
                    if not call_info["publica"]:
                        item.style = discord.ButtonStyle.red
                        item.label = "Privada"
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ erro ao carregar configurações: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="deletarcall", description="Deleta sua call personalizada")
    async def deletarcall(self, interaction: discord.Interaction):
        """Comando para deletar a call do usuário"""
        try:
            calls_data = load_calls_data()
            user_id = str(interaction.user.id)
            
            if user_id not in calls_data:
                await interaction.response.send_message("❌ você não possui uma call ativa!", ephemeral=True)
                return
            
            channel = interaction.guild.get_channel(int(calls_data[user_id]["channel_id"]))
            if channel:
                await channel.delete()
            
            del calls_data[user_id]
            save_calls_data(calls_data)
            
            await interaction.response.send_message("✅ call deletada com sucesso!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ erro ao deletar call: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="listarcalls", description="Lista todas as calls ativas (apenas admins)")
    @app_commands.checks.has_permissions(administrator=True)
    async def listarcalls(self, interaction: discord.Interaction):
        """Comando para listar todas as calls ativas"""
        try:
            calls_data = load_calls_data()
            
            if not calls_data:
                await interaction.response.send_message("📭 nenhuma call ativa no momento.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📋 calls ativas",
                color=discord.Color.blurple()
            )
            
            for user_id, call_info in calls_data.items():
                try:
                    user = await interaction.client.fetch_user(int(user_id))
                    channel = interaction.guild.get_channel(int(call_info["channel_id"]))
                    
                    if channel:
                        limite_texto = "sem limite" if call_info["limite"] == 0 else f"{call_info['limite']} pessoa(s)"
                        status_publica = "🟢 Pública" if call_info["publica"] else "🔴 Privada"
                        pessoas = len(channel.members)
                        
                        info = f"**nome:** {call_info['nome']}\n**limite:** {limite_texto}\n**status:** {status_publica}\n**pessoas:** {pessoas}"
                        embed.add_field(name=f"👤 {user.name}", value=info, inline=False)
                except Exception as e:
                    pass
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ erro ao listar calls: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Calls(bot))
