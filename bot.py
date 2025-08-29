import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

# Dicionário para armazenar dados das scrims
scrim_data = {}

# Dicionário para armazenar dados dos contratos
offer_data = {}

# Dicionário para armazenar jogadores contratados (player_id: contract_info)
contracted_players = {}

@bot.event
async def on_ready():
    print(f'{bot.user} está online!')
    try:
        synced = await bot.tree.sync()
        print(f'Sincronizados {len(synced)} comando(s) slash')
    except Exception as e:
        print(f'Erro ao sincronizar comandos: {e}')

            # Configurar atividade do bot para "Assistindo Roblox Football Organization"
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="Roblox Football Organization"
    )
    await bot.change_presence(activity=activity)
    print("Status configurado: Assistindo Roblox Football Organization")

@bot.tree.command(name="freeagency", description="Anuncia que você está em free agency")
@discord.app_commands.describe(
    posicao="Escolha sua posição principal",
    experiencia="Seu nível de experiência"
)
async def freeagency(
    interaction: discord.Interaction,
    posicao: str,
    experiencia: str = None
):
    descricao = f" {posicao}"
    
    embed = discord.Embed(
        title="🏆 [RFO] Roblox Football Organization • Free Agency",
        description=descricao,
        color=0x00ff00,
        timestamp=discord.utils.utcnow()
    )
    
    embed.add_field(
        name="👤 Jogador", 
        value=f"{interaction.user.mention}", 
        inline=False
    )
    
    if experiencia:
        embed.add_field(
            name="⭐ Experiência",
            value=experiencia,
            inline=True
        )
    
    embed.add_field(
        name="📅 Data", 
        value=discord.utils.format_dt(discord.utils.utcnow(), style='f'), 
        inline=True
    )
    
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="RFO Bot", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="scouting", description="Procura jogadores precisando de time na RFO")
@discord.app_commands.describe(
    content="O conteúdo da mensagem que aparecerá na embed"
)
async def scouting(
    interaction: discord.Interaction,
    content: str
):
    embed = discord.Embed(
        title="🔍 [RFO] Roblox Football Organization • Scouting",
        description=content,
        color=0x9932CC,
        timestamp=discord.utils.utcnow()
    )

    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="RFO Bot", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="scrim", description="Anuncia um scrim e marca o cargo")
@discord.app_commands.describe(
    gamelink="Link do jogo no Roblox (formato: https://www.roblox.com/share?code=...)",
    players="Número de jogadores (1-14)",
    content="O conteúdo da mensagem que aparecerá na embed (opcional)"
)
@discord.app_commands.choices(players=[
    discord.app_commands.Choice(name="1 jogador", value=1),
    discord.app_commands.Choice(name="2 jogadores", value=2),
    discord.app_commands.Choice(name="3 jogadores", value=3),
    discord.app_commands.Choice(name="4 jogadores", value=4),
    discord.app_commands.Choice(name="5 jogadores", value=5),
    discord.app_commands.Choice(name="6 jogadores", value=6),
    discord.app_commands.Choice(name="7 jogadores", value=7),
    discord.app_commands.Choice(name="8 jogadores", value=8),
    discord.app_commands.Choice(name="9 jogadores", value=9),
    discord.app_commands.Choice(name="10 jogadores", value=10),
    discord.app_commands.Choice(name="11 jogadores", value=11),
    discord.app_commands.Choice(name="12 jogadores", value=12),
    discord.app_commands.Choice(name="13 jogadores", value=13),
    discord.app_commands.Choice(name="14 jogadores", value=14)
])
async def scrim(
    interaction: discord.Interaction,
    gamelink: str,
    players: int,
    content: str = None
):
    
    # Verificar quantas scrims ativas o usuário já tem
    user_active_scrims = sum(1 for scrim_info in scrim_data.values() 
                            if scrim_info['organizer'] == interaction.user.id)
    
    if user_active_scrims >= 5:
        await interaction.response.send_message("❌ Você já tem 5 scrims ativas! Cancele alguma antes de criar uma nova.", ephemeral=True)
        return
    
    # Validar se é um link válido do Roblox
    if not gamelink.startswith("https://www.roblox.com/share?code="):
        await interaction.response.send_message("❌ Por favor, forneça um link válido do Roblox (formato: https://www.roblox.com/share?code=...)", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="⚔️ [RFO] Roblox Football Organization • Scrim",
        description=content if content else "Scrim aberta! Reaja com ✅ para confirmar participação.",
        color=0xFF6B35,
        timestamp=discord.utils.utcnow()
    )
    
    embed.add_field(
        name="👤 Organizador",
        value=f"{interaction.user.mention}",
        inline=True
    )
    
    embed.add_field(
        name="📅 Data",
        value=discord.utils.format_dt(discord.utils.utcnow(), style='f'),
        inline=True
    )
    
    embed.add_field(
        name="👥 Jogadores",
        value=f"0/{players} confirmados",
        inline=True
    )
    
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="RFO Bot", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    
    # Marcar o cargo específico
    role_mention = f"<@&1407375881189458132>"
    
    await interaction.response.send_message(content=role_mention, embed=embed)
    
    # Adicionar reação de confirmação
    message = await interaction.original_response()
    await message.add_reaction("✅")
    
    # Armazenar informações da scrim para monitoramento
    scrim_data[message.id] = {
        'gamelink': gamelink,
        'max_players': players,
        'organizer': interaction.user.id,
        'channel_id': interaction.channel.id,
        'completed': False  # Adicionar status para controlar se a scrim foi completada
    }

@bot.event
async def on_reaction_add(reaction, user):
    # Ignorar reações do próprio bot
    if user == bot.user:
        return
    
    # Verificar se é uma reação de confirmação em uma scrim
    if reaction.emoji == "✅" and reaction.message.id in scrim_data:
        scrim_info = scrim_data[reaction.message.id]
        
        # Verificar se a scrim já foi completada
        if scrim_info.get('completed', False):
            return
        
        # Contar reações (excluindo a do bot)
        reaction_count = reaction.count - 1
        
        # Atualizar a embed com o novo contador
        embed = reaction.message.embeds[0]
        for i, field in enumerate(embed.fields):
            if field.name == "👥 Jogadores":
                embed.set_field_at(i, name="👥 Jogadores", value=f"{reaction_count}/{scrim_info['max_players']} confirmados", inline=True)
                break
        
        await reaction.message.edit(embed=embed)
        
        # Verificar se atingiu o número máximo de jogadores
        if reaction_count >= scrim_info['max_players']:
            # Marcar a scrim como completada
            scrim_data[reaction.message.id]['completed'] = True
            
            # Criar nova embed com o gamelink
            game_embed = discord.Embed(
                title="🎮 SCRIM LOTADA!",
                description=f"A scrim está completa! Clique no link abaixo para entrar no jogo.",
                color=0x00FF00,
                timestamp=discord.utils.utcnow()
            )
            
            game_embed.add_field(
                name="🔗 Link do Jogo",
                value=scrim_info['gamelink'],
                inline=False
            )
            
            game_embed.set_footer(text="RFO Bot • Boa sorte!", icon_url=bot.user.avatar.url if bot.user.avatar else None)
            
            # Enviar nova embed marcando o cargo
            channel = bot.get_channel(scrim_info['channel_id'])
            role_mention = f"<@&1407375881189458132>"
            if channel:
                lotada_message = await channel.send(content=role_mention, embed=game_embed)
                # Salvar o ID da mensagem "SCRIM LOTADA" para poder deletá-la depois
                scrim_data[reaction.message.id]['lotada_message_id'] = lotada_message.id
    
    # Verificar se é uma reação em uma oferta de contrato
    elif reaction.message.id in offer_data:
        offer_info = offer_data[reaction.message.id]
        
        # Verificar se a oferta não expirou
        if offer_info['expired']:
            return
        
        # Verificar se é o jogador correto reagindo
        if user.id != offer_info['player']:
            return
        
        if reaction.emoji == "✅":
            # Contrato aceito
            accepted_embed = discord.Embed(
                title="🎉 CONTRACT SUCCESSFULLY SIGNED! 🎉",
                description=f"**Congratulations!** The contract has been officially signed and sealed.\n\n🤝 **{offer_info['team']}** welcomes their new **{offer_info['position']}** player!",
                color=0x2ECC71,
                timestamp=discord.utils.utcnow()
            )
            
            accepted_embed.add_field(
                name="📋 **CONTRACT DETAILS**",
                value=f"⚽ Team: {offer_info['team']}\n🎯 Position: {offer_info['position']}\n🏟️ Environment: {offer_info['environment']}\n📅 Signed: {discord.utils.utcnow().strftime('%d/%m/%Y at %H:%M')}",
                inline=False
            )
            
            # Parties involved
            accepted_embed.add_field(
                name="👤 **CONTRACTOR**",
                value=f"<@{offer_info['contractor']}>\n*Team Manager*",
                inline=True
            )
            
            accepted_embed.add_field(
                name="🎮 **PLAYER**",
                value=f"<@{offer_info['player']}>\n*New Team Member*",
                inline=True
            )
            
            accepted_embed.add_field(
                name="🆔 **CONTRACT ID**",
                value=f"`{reaction.message.id}`\n*Reference Number*",
                inline=True
            )
            
            accepted_embed.set_footer(
                text="🏆 [RFO] Roblox Football Organization • Contract Management System",
                icon_url=bot.user.avatar.url if bot.user.avatar else None
            )
            
            # Add a thumbnail (you can replace with team logo if available)
            accepted_embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1234567890123456789.png" if bot.user.avatar else None)
            
            await reaction.message.edit(embed=accepted_embed)
            await reaction.message.clear_reactions()
            offer_data[reaction.message.id]['expired'] = True
            
            # Registrar o jogador como contratado
            contracted_players[offer_info['player']] = {
                'team': offer_info['team'],
                'position': offer_info['position'],
                'environment': offer_info['environment'],
                'contractor': offer_info['contractor'],
                'contract_date': discord.utils.utcnow(),
                'contract_id': reaction.message.id
            }
            
        elif reaction.emoji == "❌":
            # Contrato rejeitado
            rejected_embed = discord.Embed(
                title="❌ Contract Rejected",
                description="This contract offer has been rejected by the player.",
                color=0xFF0000,
                timestamp=discord.utils.utcnow()
            )
            
            rejected_embed.add_field(
                name="📋 Contract Details",
                value=f"**Team:** {offer_info['team']}\n**Position:** {offer_info['position']}\n**Environment:** {offer_info['environment']}",
                inline=False
            )
            
            rejected_embed.add_field(
                name="👤 Contractor",
                value=f"<@{offer_info['contractor']}>",
                inline=True
            )
            
            rejected_embed.add_field(
                name="🎮 Player",
                value=f"<@{offer_info['player']}>",
                inline=True
            )
            
            rejected_embed.set_footer(text=f"[RFO] Roblox Football Organization • Date: {discord.utils.utcnow().strftime('%d/%m/%Y %H:%M:%S')}", icon_url=bot.user.avatar.url if bot.user.avatar else None)
            
            await reaction.message.edit(embed=rejected_embed)
            await reaction.message.clear_reactions()
            offer_data[reaction.message.id]['expired'] = True

@bot.event
async def on_reaction_remove(reaction, user):
    # Ignorar reações do próprio bot
    if user == bot.user:
        return
    
    # Verificar se é uma reação de confirmação em uma scrim ativa
    if reaction.emoji == "✅" and reaction.message.id in scrim_data:
        scrim_info = scrim_data[reaction.message.id]
        
        # Verificar se a scrim já foi completada
        if scrim_info.get('completed', False):
            return
        
        # Contar reações (excluindo a do bot)
        reaction_count = max(0, reaction.count - 1)
        
        # Atualizar a embed com o novo contador
        embed = reaction.message.embeds[0]
        for i, field in enumerate(embed.fields):
            if field.name == "👥 Jogadores":
                embed.set_field_at(i, name="👥 Jogadores", value=f"{reaction_count}/{scrim_info['max_players']} confirmados", inline=True)
                break
        
        await reaction.message.edit(embed=embed)

@bot.tree.command(name="cancel", description="Cancela sua scrim mais recente")
async def cancel(interaction: discord.Interaction):
    # Encontrar a scrim mais recente do usuário
    user_scrim = None
    latest_timestamp = 0
    
    for message_id, scrim_info in scrim_data.items():
        if scrim_info['organizer'] == interaction.user.id:
            # Usar o ID da mensagem como timestamp (IDs do Discord são baseados em tempo)
            if message_id > latest_timestamp:
                latest_timestamp = message_id
                user_scrim = (message_id, scrim_info)
    
    if not user_scrim:
        await interaction.response.send_message("❌ Você não tem nenhuma scrim ativa para cancelar!", ephemeral=True)
        return
    
    message_id, scrim_info = user_scrim
    try:
        channel = bot.get_channel(scrim_info['channel_id'])
        if channel:
            message = await channel.fetch_message(message_id)
            
            # Se a scrim estava completada e tem mensagem "SCRIM LOTADA", deletar ela
            if scrim_info.get('completed', False) and 'lotada_message_id' in scrim_info:
                try:
                    lotada_message = await channel.fetch_message(scrim_info['lotada_message_id'])
                    await lotada_message.delete()
                except discord.NotFound:
                    pass  # Mensagem já foi deletada
            
            # Criar embed de cancelamento
            cancel_embed = discord.Embed(
                title="❌ SCRIM CANCELADA!",
                description="Esta scrim foi cancelada pelo organizador.",
                color=0xFF0000,
                timestamp=discord.utils.utcnow()
            )
            
            cancel_embed.add_field(
                name="👤 Organizador",
                value=f"<@{scrim_info['organizer']}>",
                inline=False
            )
            
            cancel_embed.set_footer(text="RFO Bot • Scrim cancelada!", icon_url=bot.user.avatar.url if bot.user.avatar else None)
            
            # Substituir a embed original pela embed de cancelamento
            await message.edit(content=None, embed=cancel_embed)
            
            # Remover todas as reações
            await message.clear_reactions()
        
        # Remover do dicionário
        del scrim_data[message_id]
        await interaction.response.send_message("✅ Scrim cancelada com sucesso!", ephemeral=True)
        
    except discord.NotFound:
        # Mensagem foi deletada, apenas remove do dicionário
        del scrim_data[message_id]
        await interaction.response.send_message("✅ Scrim cancelada com sucesso!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message("❌ Erro ao cancelar a scrim. Tente novamente.", ephemeral=True)
        print(f"Erro ao cancelar scrim: {e}")

@bot.tree.command(name="offer", description="Envia uma oferta de contrato para um jogador")
@discord.app_commands.describe(
    player="Mencione o jogador para quem você quer enviar a oferta",
    team="Nome do time que está fazendo a oferta",
    position="Posição oferecida",
    environment="Ambiente do contrato (ex: TITULAR, RESERVA)"
)
async def offer(
    interaction: discord.Interaction,
    player: discord.Member,
    team: str,
    position: str,
    environment: str
):
    # Criar embed de espera
    waiting_embed = discord.Embed(
        title="⏳ Contract Pending",
        description=f"A contract offer has been sent to {player.mention}. Waiting for response...",
        color=0xFFFF00,
        timestamp=discord.utils.utcnow()
    )
    
    waiting_embed.add_field(
        name="📋 Contract Details",
        value=f"**Team:** {team}\n**Position:** {position}\n**Environment:** {environment}",
        inline=False
    )
    
    waiting_embed.add_field(
        name="👤 Contractor",
        value=interaction.user.mention,
        inline=True
    )
    
    waiting_embed.add_field(
        name="🎯 Player",
        value=player.mention,
        inline=True
    )
    
    waiting_embed.set_footer(text="Contract expires in 30 minutes", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    
    # Enviar mensagem
    await interaction.response.send_message(embed=waiting_embed)
    message = await interaction.original_response()
    
    # Adicionar reações
    await message.add_reaction("✅")
    await message.add_reaction("❌")
    
    # Armazenar dados da oferta
    offer_data[message.id] = {
        'contractor': interaction.user.id,
        'player': player.id,
        'team': team,
        'position': position,
        'environment': environment,
        'channel_id': interaction.channel.id,
        'expired': False
    }
    
    # Criar task para expirar em 30 minutos
    asyncio.create_task(expire_offer(message.id, 30 * 60))

async def expire_offer(message_id, delay):
    await asyncio.sleep(delay)
    
    if message_id in offer_data and not offer_data[message_id]['expired']:
        offer_info = offer_data[message_id]
        
        try:
            channel = bot.get_channel(offer_info['channel_id'])
            if channel:
                message = await channel.fetch_message(message_id)
                
                # Criar embed de expirado
                expired_embed = discord.Embed(
                    title="⌛ Contract Expired",
                    description="This contract offer has expired due to no response.",
                    color=0x808080,
                    timestamp=discord.utils.utcnow()
                )
                
                expired_embed.add_field(
                    name="📋 Contract Details",
                    value=f"**Team:** {offer_info['team']}\n**Position:** {offer_info['position']}\n**Environment:** {offer_info['environment']}",
                    inline=False
                )
                
                expired_embed.set_footer(text="Contract expired after 30 minutes", icon_url=bot.user.avatar.url if bot.user.avatar else None)
                
                await message.edit(embed=expired_embed)
                await message.clear_reactions()
                
                offer_data[message_id]['expired'] = True
        except discord.NotFound:
            pass
        except Exception as e:
            print(f"Erro ao expirar oferta: {e}")

@bot.tree.command(name="release", description="Libera um jogador do seu time")
@discord.app_commands.describe(
    player="Mencione o jogador que você quer liberar do time"
)
async def release(
    interaction: discord.Interaction,
    player: discord.Member
):
    # Verificar se o jogador está contratado
    if player.id not in contracted_players:
        await interaction.response.send_message("❌ Este jogador não está contratado por nenhum time!", ephemeral=True)
        return
    
    contract_info = contracted_players[player.id]
    
    # Verificar se o usuário é o mesmo que contratou o jogador
    if contract_info['contractor'] != interaction.user.id:
        await interaction.response.send_message("❌ Você só pode liberar jogadores que você mesmo contratou!", ephemeral=True)
        return
    
    # Criar embed de liberação
    release_embed = discord.Embed(
        title="🆓 Contract Released",
        description=f"The contract for player {player.mention} ( {player.id} ) has been successfully released.",
        color=0x808080,
        timestamp=discord.utils.utcnow()
    )
    
    release_embed.add_field(
        name="**Released by:**",
        value=f"{interaction.user.mention} ( {interaction.user.id} )",
        inline=False
    )
    
    # Adicionar informações do contrato liberado
    contract_duration = discord.utils.utcnow() - contract_info['contract_date']
    days = contract_duration.days
    hours = contract_duration.seconds // 3600
    
    release_embed.add_field(
        name="📋 **Previous Contract Details**",
        value=f"⚽ **Team:** {contract_info['team']}\n🎯 **Position:** {contract_info['position']}\n🏟️ **Environment:** {contract_info['environment']}\n⏱️ **Contract Duration:** {days} days, {hours} hours",
        inline=False
    )
    
    release_embed.set_footer(
        text=f"🏆 [RFO] Roblox Football Organization • Date: {discord.utils.utcnow().strftime('%d/%m/%Y %H:%M:%S')}",
        icon_url=bot.user.avatar.url if bot.user.avatar else None
    )
    
    release_embed.set_thumbnail(url=player.display_avatar.url)
    
    # Remover o jogador da lista de contratados
    del contracted_players[player.id]
    
    await interaction.response.send_message(embed=release_embed)

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("ERRO: Token do Discord não encontrado. Verifique o arquivo .env")
    else:
        bot.run(token)