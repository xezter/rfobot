import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
import json

load_dotenv()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

# Dicionário para armazenar dados das scrims
scrim_data = {}

# Dicionário para armazenar dados dos contratos
offer_data = {}

# Dicionário para armazenar jogadores contratados (player_id: contract_info)
contracted_players = {}

# Variável para controlar se o free agency está aberto
free_agency_open = True

# Dicionário para armazenar managers dos times (team_name: manager_id)
team_managers = {}

# Lista de times disponíveis
AVAILABLE_TEAMS = [
    "Corinthians", "Santos", "São Paulo", "Palmeiras", "Mirassol",
    "Flamengo", "Vasco", "Botafogo", "Fluminense", "Grêmio",
    "Internacional", "Cruzeiro", "Atlético Mineiro", "Athletico Paranaense",
    "Bahia", "Paysandu"
]

# ID do servidor da RFO
RFO_SERVER_ID = 1362995057661182034

def check_rfo_server(interaction: discord.Interaction) -> bool:
    """Verifica se o comando está sendo usado no servidor correto da RFO"""
    if not interaction.guild or interaction.guild.id != RFO_SERVER_ID:
        return False
    return True

# Funções para salvar e carregar dados

def save_data():
    """Salva todos os dados em arquivo JSON"""
    # Função para converter objetos datetime para string
    def convert_datetime(obj):
        if isinstance(obj, str):
            return obj  # já é string, retorna direto
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')
    
    # Criar cópia dos dados para manipulação
    data = {
        'free_agency_open': free_agency_open,
        'scrim_data': {},
        'offer_data': {},
        'contracted_players': {},
        'team_managers': team_managers,
        'user_recommend_count': user_recommend_count,
        'user_recommend_targets': {str(uid): list(targets) for uid, targets in user_recommend_targets.items()}
    }
    
    # Processar contracted_players
    for player_id, contract_info in contracted_players.items():
        data['contracted_players'][str(player_id)] = {
            'team': contract_info['team'],
            'position': contract_info['position'],
            'environment': contract_info['environment'],
            'contractor': contract_info['contractor'],
            'contract_date': convert_datetime(contract_info['contract_date']),
            'contract_id': contract_info['contract_id']
        }
    
    # Processar scrim_data
    for msg_id, scrim_info in scrim_data.items():
        scrim_copy = scrim_info.copy()
        if 'created_at' in scrim_copy:
            # Só converte se não for string
            if not isinstance(scrim_copy['created_at'], str):
                scrim_copy['created_at'] = convert_datetime(scrim_copy['created_at'])
        data['scrim_data'][str(msg_id)] = scrim_copy


    try:
        with open('rfo_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("✅ Dados salvos com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao salvar dados: {e}")

def load_data():
    """Carrega todos os dados do arquivo JSON"""
    global free_agency_open, scrim_data, offer_data, contracted_players, team_managers
    global user_recommend_count, user_recommend_targets

    if not os.path.exists('rfo_data.json'):
        print("📁 Arquivo de dados não encontrado. Usando configurações padrão.")
        return

    try:
        with open('rfo_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Carregar dados básicos
        free_agency_open = data.get('free_agency_open', True)
        scrim_data = data.get('scrim_data', {})
        offer_data = data.get('offer_data', {})
        team_managers = data.get('team_managers', {})

        # Carregar recomendações persistentes
        user_recommend_count = data.get('user_recommend_count', {})
        user_recommend_targets = {int(uid): set(targets) for uid, targets in data.get('user_recommend_targets', {}).items()}

        # Carregar jogadores contratados (converter string para int)
        contracted_players = {}
        for player_id_str, contract_info in data.get('contracted_players', {}).items():
            player_id = int(player_id_str)
            contracted_players[player_id] = {
                'team': contract_info['team'],
                'position': contract_info['position'],
                'environment': contract_info['environment'],
                'contractor': contract_info['contractor'],
                'contract_date': discord.utils.utcnow().fromisoformat(contract_info['contract_date']),
                'contract_id': contract_info['contract_id']
            }

        print("✅ Dados carregados com sucesso!")
        print(f"📊 Status: Free Agency {'ABERTO' if free_agency_open else 'FECHADO'}")
        print(f"⚔️ Scrims ativas: {len(scrim_data)}")
        print(f"📋 Ofertas pendentes: {len(offer_data)}")
        print(f"👥 Jogadores contratados: {len(contracted_players)}")
        print(f"🏆 Managers de times: {len(team_managers)}")

    except json.JSONDecodeError as e:
        print(f"❌ Arquivo rfo_data.json corrompido: {e}")
        print("🔄 Ignorando arquivo e usando configurações padrão...")
        return
    except Exception as e:
        print(f"❌ Erro ao carregar dados: {e}")
        print("🔄 Usando configurações padrão...")

@bot.event
async def on_ready():
    print(f'{bot.user} está online!')
    
    # Configurar atividade do bot para "Assistindo Roblox Football Organization"
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="Roblox Football Organization"
    )
    await bot.change_presence(activity=activity)
    print("Status configurado: Assistindo Roblox Football Organization")
    
    try:
        synced = await bot.tree.sync()
        print(f'Sincronizados {len(synced)} comando(s) slash')
    except Exception as e:
        print(f'Erro ao sincronizar comandos: {e}')

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
    # Verificar se o comando está sendo usado no servidor correto
    if not check_rfo_server(interaction):
        await interaction.response.send_message("❌ Este comando só pode ser usado no servidor da RFO!", ephemeral=True)
        return

    # Verificar se o jogador já tem contrato
    if str(interaction.user.id) in contracted_players:
        contract = contracted_players[str(interaction.user.id)]
        await interaction.response.send_message(
            f"❌ Você já tem um contrato ativo com o {contract['team']} e não pode entrar em free agency!",
            ephemeral=True
        )
        return

    # Verificar se o free agency está aberto
    if not free_agency_open:
        await interaction.response.send_message("❌ O Free Agency está atualmente **FECHADO**. Aguarde até que seja reaberto pelos administradores.", ephemeral=True)
        return

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

    # Enviar embed para o canal específico de free agency
    target_channel = bot.get_channel(1404959244310020218)
    if target_channel:
        await target_channel.send(content=f"{interaction.user.mention}", embed=embed)
        await interaction.response.send_message("✅ Seu anúncio de free agency foi postado com sucesso!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Erro: Canal de free agency não encontrado!", ephemeral=True)

@bot.tree.command(name="scouting", description="Procura por um jogador específico na RFO")
@discord.app_commands.describe(
    content="O conteúdo da mensagem que aparecerá na embed"
)
async def scouting(
    interaction: discord.Interaction,
    content: str
):
    # Verificar se o comando está sendo usado no servidor correto
    if not check_rfo_server(interaction):
        await interaction.response.send_message("❌ Este comando só pode ser usado no servidor da RFO!", ephemeral=True)
        return
    
    # Verificar se o sistema está aberto
    if not free_agency_open:
        await interaction.response.send_message("❌ O sistema está **FECHADO** pelos administradores. Aguarde até que seja reaberto.", ephemeral=True)
        return
    
    # Verificar se o usuário tem o cargo necessário (1362995058093326597)
    required_role_id = 1362995058093326597
    if not any(role.id == required_role_id for role in interaction.user.roles):
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🔍 [RFO] Roblox Football Organization • Scouting",
        description=content,
        color=0x9932CC,
        timestamp=discord.utils.utcnow()
    )

    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="RFO Bot", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    
    # Enviar embed para o canal específico de scouting
    target_channel = bot.get_channel(1363155113274769458)
    if target_channel:
        await target_channel.send(embed=embed)
        await interaction.response.send_message("✅ Seu anúncio de scouting foi postado com sucesso!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Erro: Canal de scouting não encontrado!", ephemeral=True)

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
    # Verificar se o comando está sendo usado no servidor correto
    if not check_rfo_server(interaction):
        await interaction.response.send_message("❌ Este comando só pode ser usado no servidor da RFO!", ephemeral=True)
        return
    
    # Verificar se o usuário tem um dos cargos necessários
    required_role_ids = [
        1362995058093326603,  # Cargo original
        1362995058114170924,  # Novo cargo
        1401738982190219294,  # Novo cargo
        1407939558376603748,  # Novo cargo
        1362995058114170929,  # Novo cargo
        1403968687571996672,  # Novo cargo
        1392991214713835681,  # Novo cargo
        1362995058114170930,  # Novo cargo
        1368684328116158575   # Novo cargo
    ]
    
    if not any(role.id in required_role_ids for role in interaction.user.roles):
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando!", ephemeral=True)
        return
    
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
        value=f"1/{players} confirmados",  # Começa com 1 (organizador)
        inline=True
    )
    
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="RFO Bot", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    
    # Enviar embed para o canal específico de scrims
    target_channel = bot.get_channel(1405640044487643216)
    if target_channel:
        message = await target_channel.send(content="@here", embed=embed)
        await interaction.response.send_message("✅ Sua scrim foi postada com sucesso!", ephemeral=True)
        
        # Adicionar reação de confirmação
        await message.add_reaction("✅")
        
        # Armazenar informações da scrim para monitoramento
        scrim_data[message.id] = {
            'gamelink': gamelink,
            'max_players': players,
            'organizer': interaction.user.id,
            'channel_id': target_channel.id,
            'completed': False,  # Adicionar status para controlar se a scrim foi completada
            'confirmed_users': [interaction.user.id],  # Lista de usuários confirmados (começa com o organizador)
            'created_at': discord.utils.utcnow(),  # Timestamp de criação
            'reinforce_count': 0  # Contador de reforços
        }
        
        # Salvar dados automaticamente
        save_data()
    else:
        await interaction.response.send_message("❌ Erro: Canal de scrims não encontrado!", ephemeral=True)

@bot.tree.command(name="cancel", description="Cancela sua scrim mais recente")
async def cancel(interaction: discord.Interaction):
    # Verificar se o comando está sendo usado no servidor correto
    if not check_rfo_server(interaction):
        await interaction.response.send_message("❌ Este comando só pode ser usado no servidor da RFO!", ephemeral=True)
        return
    
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
            
            # Limpar todas as mensagens de reforço da scrim
            if 'reinforce_messages' in scrim_info:
                for reinforce_msg_id in scrim_info['reinforce_messages']:
                    try:
                        reinforce_msg = await channel.fetch_message(reinforce_msg_id)
                        await reinforce_msg.delete()
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
        
        # Salvar dados automaticamente
        save_data()
        
        await interaction.response.send_message("✅ Scrim cancelada com sucesso!", ephemeral=True)
        
    except discord.NotFound:
        # Mensagem foi deletada, apenas remove do dicionário
        del scrim_data[message_id]
        
        # Salvar dados automaticamente
        save_data()
        
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
@discord.app_commands.choices(team=[
    discord.app_commands.Choice(name="Corinthians", value="Corinthians"),
    discord.app_commands.Choice(name="Santos", value="Santos"),
    discord.app_commands.Choice(name="São Paulo", value="São Paulo"),
    discord.app_commands.Choice(name="Palmeiras", value="Palmeiras"),
    discord.app_commands.Choice(name="Mirassol", value="Mirassol"),
    discord.app_commands.Choice(name="Flamengo", value="Flamengo"),
    discord.app_commands.Choice(name="Vasco", value="Vasco"),
    discord.app_commands.Choice(name="Botafogo", value="Botafogo"),
    discord.app_commands.Choice(name="Fluminense", value="Fluminense"),
    discord.app_commands.Choice(name="Grêmio", value="Grêmio"),
    discord.app_commands.Choice(name="Internacional", value="Internacional"),
    discord.app_commands.Choice(name="Cruzeiro", value="Cruzeiro"),
    discord.app_commands.Choice(name="Atlético Mineiro", value="Atlético Mineiro"),
    discord.app_commands.Choice(name="Athletico Paranaense", value="Athletico Paranaense"),
    discord.app_commands.Choice(name="Bahia", value="Bahia"),
    discord.app_commands.Choice(name="Paysandu", value="Paysandu")
])
async def offer(
    interaction: discord.Interaction,
    player: discord.Member,
    team: str,
    position: str,
    environment: str
):
    # Verificar se o comando está sendo usado no servidor correto
    if not check_rfo_server(interaction):
        await interaction.response.send_message("❌ Este comando só pode ser usado no servidor da RFO!", ephemeral=True)
        return
    
    # Verificar se o sistema está aberto
    if not free_agency_open:
        await interaction.response.send_message("❌ O sistema está **FECHADO** pelos administradores. Aguarde até que seja reaberto.", ephemeral=True)
        return
    
    # Verificar se o usuário tem o cargo necessário (1362995058093326597)
    required_role_id = 1362995058093326597
    if not any(role.id == required_role_id for role in interaction.user.roles):
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando!", ephemeral=True)
        return
    
    # Verificar se o jogador já está contratado
    if player.id in contracted_players:
        current_contract = contracted_players[player.id]
        
        # Verificar se o jogador já está no time do próprio manager
        if current_contract['team'] in user_managed_teams:
            await interaction.response.send_message(
                f"❌ **ERRO:** {player.mention} já está contratado pelo **SEU** time **{current_contract['team']}**!\n"
                f"💡 **Dica:** Se você quiser alterar o contrato dele, use `/release` primeiro e depois `/offer` novamente.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ **ERRO:** {player.mention} já está contratado pelo time **{current_contract['team']}**!\n"
                f"🎯 Posição: {current_contract['position']}\n"
                f"🏟️ Ambiente: {current_contract['environment']}\n"
                f"📅 Contratado em: {current_contract['contract_date'].strftime('%d/%m/%Y')}",
                ephemeral=True
            )
        return
    
    # Verificar se o usuário é manager de algum time
    user_managed_teams = [team_name for team_name, manager_id in team_managers.items() if manager_id == interaction.user.id]
    
    if not user_managed_teams:
        await interaction.response.send_message("❌ Você não é manager de nenhum time! Use `/setmanager` para se tornar manager de um time.", ephemeral=True)
        return
    
    # Verificar se o time escolhido é um dos times que o usuário gerencia
    if team not in user_managed_teams:
        await interaction.response.send_message(
            f"❌ Você só pode fazer ofertas para times que você gerencia!\n"
            f"🏆 Seus times: {', '.join(user_managed_teams)}\n"
            f"🎯 Time escolhido: {team}",
            ephemeral=True
        )
        return
    
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
    
    waiting_embed.set_footer(text="Contract expires in 24 hours", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    
    # Enviar mensagem para o canal específico de ofertas
    target_channel = bot.get_channel(1384358960227942531)
    if target_channel:
        message = await target_channel.send(f"{player.mention}", embed=waiting_embed)
        await interaction.response.send_message("✅ Sua oferta de contrato foi postada com sucesso!", ephemeral=True)
        
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
            'channel_id': target_channel.id,
            'expired': False
        }
        
        # Criar task para expirar em um dia
        asyncio.create_task(expire_offer(message.id, 24 * 60 * 60))
        
        # Salvar dados automaticamente
        save_data()
    else:
        await interaction.response.send_message("❌ Erro: Canal de ofertas não encontrado!", ephemeral=True)

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
                
                expired_embed.set_footer(text="Contract expired after 24 hours", icon_url=bot.user.avatar.url if bot.user.avatar else None)
                
                await message.edit(embed=expired_embed)
                await message.clear_reactions()
                
                offer_data[message_id]['expired'] = True
                
                # Salvar dados automaticamente
                save_data()
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
    # Verificar se o comando está sendo usado no servidor correto
    if not check_rfo_server(interaction):
        await interaction.response.send_message("❌ Este comando só pode ser usado no servidor da RFO!", ephemeral=True)
        return
    
    # Verificar se o sistema está aberto
    if not free_agency_open:
        await interaction.response.send_message("❌ O sistema está **FECHADO** pelos administradores. Aguarde até que seja reaberto.", ephemeral=True)
        return
    
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
    
    # Salvar dados automaticamente
    save_data()
    
    await interaction.response.send_message(embed=release_embed)

@bot.tree.command(name="players", description="Mostra todos os jogadores contratados por time (apenas administradores)")
async def players(interaction: discord.Interaction):
    # Verificar se o comando está sendo usado no servidor correto
    if not check_rfo_server(interaction):
        await interaction.response.send_message("❌ Este comando só pode ser usado no servidor da RFO!", ephemeral=True)
        return
    
    # Verificar se o usuário é administrador
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando! Apenas administradores podem ver os players.", ephemeral=True)
        return

    # Criar view com seleção de times
    view = PlayersSelectView()
    
    embed = discord.Embed(
        title="🏆 [RFO] Jogadores por Time",
        description="Selecione um time abaixo para ver todos os jogadores contratados:",
        color=0x0099FF,
        timestamp=discord.utils.utcnow()
    )
    
    embed.set_footer(text="🏆 [RFO] Roblox Football Organization", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class PlayersSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)  # 5 minutos de timeout

    @discord.ui.select(
        placeholder="Escolha um time para ver os jogadores...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="Corinthians", value="Corinthians", emoji="⚽"),
            discord.SelectOption(label="Santos", value="Santos", emoji="⚽"),
            discord.SelectOption(label="São Paulo", value="São Paulo", emoji="⚽"),
            discord.SelectOption(label="Palmeiras", value="Palmeiras", emoji="⚽"),
            discord.SelectOption(label="Mirassol", value="Mirassol", emoji="⚽"),
            discord.SelectOption(label="Flamengo", value="Flamengo", emoji="⚽"),
            discord.SelectOption(label="Vasco", value="Vasco", emoji="⚽"),
            discord.SelectOption(label="Botafogo", value="Botafogo", emoji="⚽"),
            discord.SelectOption(label="Fluminense", value="Fluminense", emoji="⚽"),
            discord.SelectOption(label="Grêmio", value="Grêmio", emoji="⚽"),
            discord.SelectOption(label="Internacional", value="Internacional", emoji="⚽"),
            discord.SelectOption(label="Cruzeiro", value="Cruzeiro", emoji="⚽"),
            discord.SelectOption(label="Atlético Mineiro", value="Atlético Mineiro", emoji="⚽"),
            discord.SelectOption(label="Athletico Paranaense", value="Athletico Paranaense", emoji="⚽"),
            discord.SelectOption(label="Bahia", value="Bahia", emoji="⚽"),
            discord.SelectOption(label="Paysandu", value="Paysandu", emoji="⚽"),
        ]
    )
    async def select_team(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_team = select.values[0]
        
        # Filtrar jogadores do time selecionado
        team_players = []
        for player_id, contract_info in contracted_players.items():
            if contract_info['team'] == selected_team:
                player = interaction.guild.get_member(player_id)
                if player:
                    team_players.append({
                        'player': player,
                        'contract_info': contract_info
                    })
        
        # Criar embed com os jogadores do time
        embed = discord.Embed(
            title=f"⚽ {selected_team} - Jogadores Contratados",
            color=0x00FF00 if team_players else 0xFF0000,
            timestamp=discord.utils.utcnow()
        )
        
        if team_players:
            embed.description = f"**Total de jogadores:** {len(team_players)}"
            
            # Adicionar manager do time se existir
            if selected_team in team_managers:
                manager_id = team_managers[selected_team]
                manager = interaction.guild.get_member(manager_id)
                manager_mention = manager.mention if manager else f"<@{manager_id}>"
                embed.add_field(
                    name="👤 Manager",
                    value=manager_mention,
                    inline=False
                )
            
            # Adicionar cada jogador
            for i, player_data in enumerate(team_players, 1):
                player = player_data['player']
                contract = player_data['contract_info']
                
                # Calcular tempo de contrato
                contract_duration = discord.utils.utcnow() - contract['contract_date']
                days = contract_duration.days
                hours = contract_duration.seconds // 3600
                
                embed.add_field(
                    name=f"🎮 Jogador {i}",
                    value=(
                        f"**Player:** {player.mention}\n"
                        f"**Posição:** {contract['position']}\n"
                        f"**Ambiente:** {contract['environment']}\n"
                        f"**Contratado há:** {days}d {hours}h\n"
                        f"**ID do Contrato:** `{contract['contract_id']}`"
                    ),
                    inline=True
                )
        else:
            embed.description = "Este time não possui jogadores contratados no momento."
            embed.add_field(
                name="📋 Status",
                value="Nenhum jogador encontrado",
                inline=False
            )
            
            # Verificar se tem manager
            if selected_team in team_managers:
                manager_id = team_managers[selected_team]
                manager = interaction.guild.get_member(manager_id)
                manager_mention = manager.mention if manager else f"<@{manager_id}>"
                embed.add_field(
                    name="👤 Manager",
                    value=manager_mention,
                    inline=False
                )
            else:
                embed.add_field(
                    name="👤 Manager",
                    value="**N/A**",
                    inline=False
                )
        
        embed.set_footer(text="🏆 [RFO] Roblox Football Organization", icon_url=bot.user.avatar.url if bot.user.avatar else None)
        
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        # Desabilitar o select quando o timeout for atingido
        for item in self.children:
            item.disabled = True

@bot.tree.command(name="friendly", description="Anuncia que seu time está buscando um amistoso (apenas managers)")
async def friendly(interaction: discord.Interaction):
    # Verificar se o comando está sendo usado no servidor correto
    if not check_rfo_server(interaction):
        await interaction.response.send_message("❌ Este comando só pode ser usado no servidor da RFO!", ephemeral=True)
        return

    # Verificar se o usuário é manager de algum time
    user_team = None
    for team, manager_id in team_managers.items():
        if manager_id == interaction.user.id:
            user_team = team
            break

    if not user_team:
        await interaction.response.send_message("❌ Apenas managers podem anunciar amistosos!", ephemeral=True)
        return

    embed = discord.Embed(
        title="🤝 Procurando Amistoso!",
        description=f"O manager {interaction.user.mention} está buscando um amistoso para seu time!",
        color=0x3498db,
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="🏆 Time", value=user_team, inline=True)
    embed.add_field(name="👤 Manager", value=interaction.user.mention, inline=True)
    embed.set_footer(text="RFO Bot • Chame o manager no privado para combinar o amistoso", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)

    target_channel = bot.get_channel(1409125931204870185)
    if target_channel:
        await target_channel.send(content="<@&1362995058093326597>", embed=embed)
        await interaction.response.send_message("✅ Seu anúncio de amistoso foi enviado!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Erro: Canal de amistosos não encontrado!", ephemeral=True)

@bot.tree.command(name="reforce", description="Reforça uma scrim para chamar mais jogadores")
async def reforce(interaction: discord.Interaction):
    # Verificar se o comando está sendo usado no servidor correto
    if not check_rfo_server(interaction):
        await interaction.response.send_message("❌ Este comando só pode ser usado no servidor da RFO!", ephemeral=True)
        return
    
    # Verificar se o usuário tem uma scrim ativa no canal correto
    user_scrim = None
    for message_id, scrim_info in scrim_data.items():
        if (scrim_info['organizer'] == interaction.user.id and 
            scrim_info['channel_id'] == 1405640044487643216):
            user_scrim = (message_id, scrim_info)
            break
    
    if not user_scrim:
        await interaction.response.send_message("❌ Você não tem nenhuma scrim ativa no canal de scrims para reforçar!", ephemeral=True)
        return
    
    message_id, scrim_info = user_scrim
    
    # Verificar se a scrim já foi completada
    if scrim_info.get('completed', False):
        await interaction.response.send_message("❌ Não é possível reforçar uma scrim que já foi completada!", ephemeral=True)
        return
    
    # Inicializar contador de reforços se não existir
    if 'reinforce_count' not in scrim_info:
        scrim_info['reinforce_count'] = 0
    
    # Verificar se já atingiu o limite de 3 reforços
    if scrim_info['reinforce_count'] >= 3:
        await interaction.response.send_message("❌ Você já usou o máximo de 3 reforços para esta scrim!", ephemeral=True)
        return
    
    # Incrementar contador de reforços
    scrim_info['reinforce_count'] += 1
    
    # Criar embed de reforço
    reforce_embed = discord.Embed(
        title="🔄 REFORÇO DE SCRIM!",
        description=f"**{interaction.user.mention}** está reforçando sua scrim para chamar mais jogadores!",
        color=0xFFA500,
        timestamp=discord.utils.utcnow()
    )
    
    reforce_embed.add_field(
        name="👤 Organizador",
        value=f"{interaction.user.mention}",
        inline=True
    )
    
    reforce_embed.add_field(
        name="📅 Data/Hora",
        value=discord.utils.format_dt(discord.utils.utcnow(), style='f'),
        inline=True
    )
    
    reforce_embed.add_field(
        name="🔄 Reforço",
        value=f"{scrim_info['reinforce_count']}/3",
        inline=True
    )
    
    reforce_embed.set_thumbnail(url=interaction.user.display_avatar.url)
    reforce_embed.set_footer(text="RFO Bot • Reforço de Scrim", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    
    # Enviar embed de reforço marcando @here
    target_channel = bot.get_channel(1405640044487643216)
    if target_channel:
        reforce_message = await target_channel.send(content="@here", embed=reforce_embed)
        
        # Armazenar ID da mensagem de reforço para limpeza posterior
        if 'reinforce_messages' not in scrim_info:
            scrim_info['reinforce_messages'] = []
        scrim_info['reinforce_messages'].append(reforce_message.id)
        
        # Salvar dados automaticamente
        save_data()
        
        await interaction.response.send_message(f"✅ Reforço enviado com sucesso! ({scrim_info['reinforce_count']}/3)", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Erro: Canal de scrims não encontrado!", ephemeral=True)


@bot.tree.command(name="recommend", description="Recomende um jogador para algum time")
@discord.app_commands.describe(
    player="Mencione o jogador recomendado",
    reason="Por que você recomenda esse jogador?",
    information="Informações relevantes sobre o jogador"
)
async def reccomend(
    interaction: discord.Interaction,
    player: discord.Member,
    reason: str,
    information: str
):
    # Impede recomendar a si mesmo
    if player.id == interaction.user.id:
        await interaction.response.send_message("❌ Você não pode recomendar a si mesmo!", ephemeral=True)
        return

    # Limite de recomendações por usuário
    user_id = interaction.user.id
    if user_id not in user_recommend_count:
        user_recommend_count[user_id] = 0
    if user_recommend_count[user_id] >= 3:
        await interaction.response.send_message("❌ Você já atingiu o limite de 3 recomendações!", ephemeral=True)
        return

    channel_id = 1409158074790318182
    channel = bot.get_channel(channel_id)
    if not channel:
        await interaction.response.send_message("❌ Canal de recomendações não encontrado!", ephemeral=True)
        return

    embed = discord.Embed(
        title="⭐ Player Recommendation",
        description=f"A new player recommendation has been submitted by {interaction.user.mention}.",
        color=0xFDBB30,
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(
        name="**Player:**",
        value=f"{player.mention} ({player.id})",
        inline=False
    )
    embed.add_field(
        name="📝 | Why I recommend them",
        value=reason,
        inline=False
    )
    embed.add_field(
        name="ℹ️ | Information",
        value=information,
        inline=False
    )
    embed.set_footer(
        text=f"[RFO] Roblox Football Organization • Date: {discord.utils.utcnow().strftime('%d/%m/%Y %H:%M:%S')}"
    )
    embed.set_thumbnail(url=player.display_avatar.url)

    await channel.send(content=f"🔔 | Player recommendation for {player.mention} ( {player.id} )", embed=embed)
    user_recommend_count[user_id] += 1
    await interaction.response.send_message(f"✅ Recomendação enviada com sucesso! ({user_recommend_count[user_id]}/3)", ephemeral=True)

@bot.tree.command(name="openall", description="Abre todos os sistemas (apenas administradores)")
async def openall(interaction: discord.Interaction):
    # Verificar se o comando está sendo usado no servidor correto
    if not check_rfo_server(interaction):
        await interaction.response.send_message("❌ Este comando só pode ser usado no servidor da RFO!", ephemeral=True)
        return
    
    # Verificar se o usuário é administrador
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando! Apenas administradores podem controlar os sistemas.", ephemeral=True)
        return
    
    global free_agency_open
    
    if free_agency_open:
        await interaction.response.send_message("ℹ️ Todos os sistemas já estão **ABERTOS**!", ephemeral=True)
        return
    
    free_agency_open = True
    
    # Criar embed de anúncio
    open_embed = discord.Embed(
        title="🟢 TODOS OS SISTEMAS ABERTOS!",
        description="Todos os sistemas foram **ABERTOS** pelos administradores!\n\n✅ Os jogadores já podem usar:\n• `/freeagency` para se anunciar\n• `/scouting` para procurar jogadores\n• `/offer` para enviar ofertas\n• `/release` para liberar jogadores",
        color=0x00FF00,
        timestamp=discord.utils.utcnow()
    )
    
    open_embed.add_field(
        name="👤 Aberto por:",
        value=f"{interaction.user.mention}",
        inline=True
    )
    
    open_embed.add_field(
        name="📅 Data/Hora:",
        value=discord.utils.format_dt(discord.utils.utcnow(), style='f'),
        inline=True
    )
    
    open_embed.set_footer(text="🏆 [RFO] Roblox Football Organization", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    
    # Enviar para o canal de free agency
    target_channel = bot.get_channel(1404959244310020218)
    if target_channel:
        await target_channel.send(embed=open_embed)
        await interaction.response.send_message("✅ Todos os sistemas foram **ABERTOS** com sucesso!", ephemeral=True)
    else:
        await interaction.response.send_message("✅ Todos os sistemas foram **ABERTOS** com sucesso! (Canal não encontrado para anúncio público)", ephemeral=True)
    
    # Salvar dados automaticamente
    save_data()

@bot.tree.command(name="closeall", description="Fecha todos os sistemas (apenas administradores)")
async def closeall(interaction: discord.Interaction):
    # Verificar se o comando está sendo usado no servidor correto
    if not check_rfo_server(interaction):
        await interaction.response.send_message("❌ Este comando só pode ser usado no servidor da RFO!", ephemeral=True)
        return
    
    # Verificar se o usuário é administrador
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando! Apenas administradores podem controlar os sistemas.", ephemeral=True)
        return
    
    global free_agency_open
    
    if not free_agency_open:
        await interaction.response.send_message("ℹ️ Todos os sistemas já estão **FECHADOS**!", ephemeral=True)
        return
    
    free_agency_open = False
    
    # Criar embed de anúncio
    close_embed = discord.Embed(
        title="🔴 TODOS OS SISTEMAS FECHADOS!",
        description="Todos os sistemas foram **FECHADOS** pelos administradores!\n\n❌ Os jogadores não podem mais usar:\n• `/freeagency` para se anunciar\n• `/scouting` para procurar jogadores\n• `/offer` para enviar ofertas\n• `/release` para liberar jogadores",
        color=0xFF0000,
        timestamp=discord.utils.utcnow()
    )
    
    close_embed.add_field(
        name="👤 Fechado por:",
        value=f"{interaction.user.mention}",
        inline=True
    )
    
    close_embed.add_field(
        name="📅 Data/Hora:",
        value=discord.utils.format_dt(discord.utils.utcnow(), style='f'),
        inline=True
    )
    
    close_embed.set_footer(text="🏆 [RFO] Roblox Football Organization", icon_url=bot.user.avatar.url if bot.user.avatar.url else None)
    
    # Enviar para o canal de free agency
    target_channel = bot.get_channel(1404959244310020218)
    if target_channel:
        await target_channel.send(embed=close_embed)
        await interaction.response.send_message("✅ Todos os sistemas foram **FECHADOS** com sucesso!", ephemeral=True)
    else:
        await interaction.response.send_message("✅ Todos os sistemas foram **FECHADOS** com sucesso! (Canal não encontrado para anúncio público)", ephemeral=True)
    
    # Salvar dados automaticamente
    save_data()

async def finalize_scrim_after_delay(message_id, delay):
    """Finaliza uma scrim após o tempo especificado"""
    await asyncio.sleep(delay)
    
    if message_id in scrim_data:
        scrim_info = scrim_data[message_id]
        
        try:
            channel = bot.get_channel(scrim_info['channel_id'])
            if channel:
                # Enviar mensagem de finalização
                finalize_embed = discord.Embed(
                    title="🏁 SCRIM FINALIZADA!",
                    description="Esta scrim foi automaticamente finalizada após 2 horas.",
                    color=0x808080,
                    timestamp=discord.utils.utcnow()
                )
                
                finalize_embed.add_field(
                    name="👤 Organizador",
                    value=f"<@{scrim_info['organizer']}>",
                    inline=True
                )
                
                finalize_embed.add_field(
                    name="⏰ Tempo de Vida",
                    value="2 horas",
                    inline=True
                )
                
                finalize_embed.set_footer(text="RFO Bot • Scrim finalizada automaticamente", icon_url=bot.user.avatar.url if bot.user.avatar else None)
                
                await channel.send(embed=finalize_embed)
                
                # Remover a scrim dos dados
                del scrim_data[message_id]
                
                # Salvar dados automaticamente
                save_data()
                
        except Exception as e:
            print(f"Erro ao finalizar scrim {message_id}: {e}")

@bot.tree.command(name="setmanager", description="Define um usuário como manager de um time (apenas administradores)")
@discord.app_commands.describe(
    team="Time para o qual o usuário será manager",
    user="Usuário que será definido como manager"
)
@discord.app_commands.choices(team=[
    discord.app_commands.Choice(name="Corinthians", value="Corinthians"),
    discord.app_commands.Choice(name="Santos", value="Santos"),
    discord.app_commands.Choice(name="São Paulo", value="São Paulo"),
    discord.app_commands.Choice(name="Palmeiras", value="Palmeiras"),
    discord.app_commands.Choice(name="Mirassol", value="Mirassol"),
    discord.app_commands.Choice(name="Flamengo", value="Flamengo"),
    discord.app_commands.Choice(name="Vasco", value="Vasco"),
    discord.app_commands.Choice(name="Botafogo", value="Botafogo"),
    discord.app_commands.Choice(name="Fluminense", value="Fluminense"),
    discord.app_commands.Choice(name="Grêmio", value="Grêmio"),
    discord.app_commands.Choice(name="Internacional", value="Internacional"),
    discord.app_commands.Choice(name="Cruzeiro", value="Cruzeiro"),
    discord.app_commands.Choice(name="Atlético Mineiro", value="Atlético Mineiro"),
    discord.app_commands.Choice(name="Athletico Paranaense", value="Athletico Paranaense"),
    discord.app_commands.Choice(name="Bahia", value="Bahia"),
    discord.app_commands.Choice(name="Paysandu", value="Paysandu")
])
async def setmanager(interaction: discord.Interaction, team: str, user: discord.Member):
    # Verificar se o comando está sendo usado no servidor correto
    if not check_rfo_server(interaction):
        await interaction.response.send_message("❌ Este comando só pode ser usado no servidor da RFO!", ephemeral=True)
        return
    
    # Verificar se o usuário é administrador
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando! Apenas administradores podem definir managers.", ephemeral=True)
        return
    
    # Verificar se o time já tem um manager
    if team in team_managers:
        old_manager_id = team_managers[team]
        old_manager = interaction.guild.get_member(old_manager_id)
        old_manager_mention = old_manager.mention if old_manager else f"<@{old_manager_id}>"
        
        await interaction.response.send_message(
            f"⚠️ O time **{team}** já tem um manager: {old_manager_mention}\n"
            f"Use `/removemanager` primeiro para remover o manager atual.",
            ephemeral=True
        )
        return
    
    # Verificar se o usuário já é manager de outro time
    if user.id in team_managers.values():
        current_team = [team_name for team_name, manager_id in team_managers.items() if manager_id == user.id][0]
        await interaction.response.send_message(
            f"⚠️ **{user.mention}** já é manager do time **{current_team}**!\n"
            f"Um usuário só pode ser manager de um time por vez.\n"
            f"Use `/removemanager @{user.name}` primeiro para remover o manager atual.",
            ephemeral=True
        )
        return
    
    # Definir o novo manager
    team_managers[team] = user.id
    
    # Salvar dados automaticamente
    save_data()
    
    # Criar embed de confirmação
    confirm_embed = discord.Embed(
        title="🏆 Manager Definido!",
        description=f"**{user.mention}** foi definido como manager do time **{team}**!",
        color=0x00FF00,
        timestamp=discord.utils.utcnow()
    )
    
    confirm_embed.add_field(
        name="👤 Manager",
        value=user.mention,
        inline=True
    )
    
    confirm_embed.add_field(
        name="🏆 Time",
        value=team,
        inline=True
    )
    
    confirm_embed.add_field(
        name="👑 Definido por",
        value=interaction.user.mention,
        inline=True
    )
    
    confirm_embed.set_footer(text="🏆 [RFO] Roblox Football Organization", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    
    await interaction.response.send_message(embed=confirm_embed)

@bot.tree.command(name="removemanager", description="Remove um manager de um time e libera todos os jogadores contratados (apenas administradores)")
@discord.app_commands.describe(
    user="Manager que será removido"
)
async def removemanager(interaction: discord.Interaction, user: discord.Member):
    # Verificar se o comando está sendo usado no servidor correto
    if not check_rfo_server(interaction):
        await interaction.response.send_message("❌ Este comando só pode ser usado no servidor da RFO!", ephemeral=True)
        return
    
    # Verificar se o usuário é administrador
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando! Apenas administradores podem remover managers.", ephemeral=True)
        return
    
    # Encontrar times que o usuário gerencia
    user_teams = [team_name for team_name, manager_id in team_managers.items() if manager_id == user.id]
    
    if not user_teams:
        await interaction.response.send_message("❌ Este usuário não é manager de nenhum time!", ephemeral=True)
        return
    
    # Contar jogadores que serão liberados
    players_to_release = []
    for player_id, contract_info in contracted_players.items():
        if contract_info['team'] in user_teams:
            players_to_release.append((player_id, contract_info))
    
    # Remover o usuário como manager dos times
    for team in user_teams:
        del team_managers[team]
    
    # Liberar todos os jogadores contratados pelos times do manager
    for player_id, contract_info in players_to_release:
        del contracted_players[player_id]
    
    # Salvar dados automaticamente
    save_data()
    
    # Criar embed de confirmação
    confirm_embed = discord.Embed(
        title="🗑️ Manager Removido!",
        description=f"**{user.mention}** foi removido como manager de **{len(user_teams)} time(s)**!",
        color=0xFF0000,
        timestamp=discord.utils.utcnow()
    )
    
    confirm_embed.add_field(
        name="👤 Manager Removido",
        value=user.mention,
        inline=True
    )
    
    confirm_embed.add_field(
        name="🏆 Times Afetados",
        value="\n".join([f"• {team}" for team in user_teams]),
        inline=False
    )
    
    if players_to_release:
        confirm_embed.add_field(
            name="🆓 Jogadores Liberados",
            value=f"**{len(players_to_release)}** jogadores foram automaticamente liberados dos times.",
            inline=False
        )
    else:
        confirm_embed.add_field(
            name="🆓 Jogadores Liberados",
            value="Nenhum jogador foi liberado (não havia jogadores contratados).",
            inline=False
        )
    
    confirm_embed.add_field(
        name="👑 Removido por",
        value=interaction.user.mention,
        inline=True
    )
    
    confirm_embed.set_footer(text="🏆 [RFO] Roblox Football Organization", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    
    await interaction.response.send_message(embed=confirm_embed)

@bot.tree.command(name="clubs", description="Mostra todos os times e seus managers (apenas administradores)")
async def clubs(interaction: discord.Interaction):
    # Verificar se o comando está sendo usado no servidor correto
    if not check_rfo_server(interaction):
        await interaction.response.send_message("❌ Este comando só pode ser usado no servidor da RFO!", ephemeral=True)
        return
    
    # Verificar se o usuário é administrador
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando! Apenas administradores podem ver os clubs.", ephemeral=True)
        return
    
    # Criar embed com todos os times
    clubs_embed = discord.Embed(
        title="🏆 [RFO] Roblox Football Organization • Clubs",
        description="Lista de todos os times e seus managers:",
        color=0x0099FF,
        timestamp=discord.utils.utcnow()
    )
    
    # Adicionar cada time ao embed
    for team in AVAILABLE_TEAMS:
        if team in team_managers:
            manager_id = team_managers[team]
            manager = interaction.guild.get_member(manager_id)
            manager_name = manager.mention if manager else f"<@{manager_id}>"
            clubs_embed.add_field(
                name=f"⚽ {team}",
                value=f"👤 Manager: {manager_name}",
                inline=True
            )
        else:
            clubs_embed.add_field(
                name=f"⚽ {team}",
                value="👤 Manager: **N/A**",
                inline=True
            )
    
    clubs_embed.set_footer(text="🏆 [RFO] Roblox Football Organization", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    
    await interaction.response.send_message(embed=clubs_embed)

# Função para limpar dados antigos periodicamente
async def cleanup_old_data():
    while True:
        try:
            current_time = discord.utils.utcnow()
            
            # Limpar scrims antigas (mais de 2 horas após completadas)
            scrims_to_remove = []
            for message_id, scrim_info in scrim_data.items():
                if scrim_info.get('completed', False):
                    # Se a scrim foi completada, verificar se já passou das 2 horas
                    if 'created_at' in scrim_info:
                        scrim_age = current_time - scrim_info['created_at']
                        if scrim_age.total_seconds() > 2 * 3600:  # 2 horas
                            scrims_to_remove.append(message_id)
            
            # Remover scrims antigas
            for message_id in scrims_to_remove:
                del scrim_data[message_id]
            
            # Limpar ofertas expiradas antigas (mais de 1 hora após expiração)
            offers_to_remove = []
            for message_id, offer_info in offer_data.items():
                if offer_info.get('expired', False):
                    # Verificar se a oferta expirou há mais de 1 hora
                    if 'expired_at' in offer_info:
                        expired_age = current_time - offer_info['expired_at']
                        if expired_age.total_seconds() > 3600:  # 1 hora
                            offers_to_remove.append(message_id)
            
            # Remover ofertas antigas
            for message_id in offers_to_remove:
                del offer_data[message_id]
            
            if scrims_to_remove or offers_to_remove:
                print(f"Limpeza automática: {len(scrims_to_remove)} scrims e {len(offers_to_remove)} ofertas removidas")
                # Salvar dados após limpeza
                save_data()
            
        except Exception as e:
            print(f"Erro na limpeza automática: {e}")
        
        # Executar limpeza a cada 6 horas
        await asyncio.sleep(6 * 3600)

# Iniciar task de limpeza automática
@bot.event
async def on_ready():
    print(f'{bot.user} está online!')
    
    # Configurar atividade do bot para "Assistindo Roblox Football Organization"
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="Roblox Football Organization"
    )
    await bot.change_presence(activity=activity)
    print("Status configurado: Assistindo Roblox Football Organization")
    
    try:
        synced = await bot.tree.sync()
        print(f'Sincronizados {len(synced)} comando(s) slash')
    except Exception as e:
        print(f'Erro ao sincronizar comandos: {e}')
    
    # Iniciar limpeza automática
    bot.loop.create_task(cleanup_old_data())
    print("Sistema de limpeza automática iniciado")
    # Carregar dados do arquivo JSON
    load_data()
    print("Dados carregados do arquivo rfo_data.json")

@bot.tree.command(name="changeplayer", description="[ADMIN] Transfere um jogador de um time para outro")
@discord.app_commands.describe(
    player="Mencione o jogador que será transferido",
    current_team="Time atual do jogador",
    new_team="Novo time do jogador"
)
@discord.app_commands.choices(
    current_team=[discord.app_commands.Choice(name=team, value=team) for team in AVAILABLE_TEAMS],
    new_team=[discord.app_commands.Choice(name=team, value=team) for team in AVAILABLE_TEAMS]
)
async def changeplayer(
    interaction: discord.Interaction,
    player: discord.Member,
    current_team: str,
    new_team: str
):
    # Verificar se o comando está sendo usado no servidor correto
    if not check_rfo_server(interaction):
        await interaction.response.send_message("❌ Este comando só pode ser usado no servidor da RFO!", ephemeral=True)
        return
    
    # Verificar se o usuário tem permissão de administrador
    ADMIN_ROLE_ID = 1362995058093326597
    if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando!", ephemeral=True)
        return
    
    # Verificar se o jogador tem um contrato ativo
    player_has_contract = False
    for player_id in contracted_players:
        if str(player_id) == str(player.id):
            player_has_contract = True
            break
    
    if not player_has_contract:
        await interaction.response.send_message(
            f"❌ {player.mention} não tem um contrato ativo no sistema!",
            ephemeral=True
        )
        return
    
    # Verificar se o jogador está no time especificado
    player_contract = None
    for player_id, contract in contracted_players.items():
        if str(player_id) == str(player.id):
            if contract['team'] == current_team:
                player_contract = contract
                break
            else:
                await interaction.response.send_message(
                    f"❌ {player.mention} não está no time {current_team}! O time atual é {contract['team']}.",
                    ephemeral=True
                )
                return
    
    try:
        # Atualizar o time do jogador
        player_contract['team'] = new_team
        
        # Salvar as alterações
        save_data()
        
        # Criar embed de confirmação
        embed = discord.Embed(
            title="🔄 TRANSFERÊNCIA DE JOGADOR",
            color=0x00FF00,
            timestamp=discord.utils.utcnow()
        )
        
        # Adicionar thumbnail do servidor se disponível
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
            
        # Adicionar descrição principal
        embed.description = (
            f"### ⚽ {player.mention} foi transferido!\n"
            f"**Posição:** {player_contract['position']}\n"
            f"**Time Anterior:** {current_team}\n"
            f"**Novo Time:** {new_team}\n"
            f"**Contratado por:** <@{player_contract['contractor']}>"
        )
        
        # Adicionar rodapé
        embed.set_footer(
            text=f"Transferência realizada por {interaction.user.display_name} • {discord.utils.utcnow().strftime('%d/%m/%Y %H:%M')}"
        )
        
        # Enviar a embed
        await interaction.response.send_message(embed=embed)
        
        # Enviar notificação no canal específico
        notification_channel = bot.get_channel(1384358960227942531)
        if notification_channel:
            await notification_channel.send(embed=embed)
            
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Ocorreu um erro ao transferir o jogador: {str(e)}",
            ephemeral=True
        )
        print(f"Erro em /changeteam: {str(e)}")

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("ERRO: Token do Discord não encontrado. Verifique o arquivo .env")
        print("Crie um arquivo .env com: DISCORD_TOKEN=seu_token_aqui")
    else:
        print("Iniciando bot RFO...")
        print("Comandos disponíveis:")
        print("- /freeagency - Anunciar free agency")
        print("- /scouting - Procurar jogadores")
        print("- /scrim - Anunciar scrim")
        print("- /cancel - Cancelar scrim")
        print("- /reforce - Reforçar scrim (máx 3x)")
        print("- /offer - Enviar oferta de contrato")
        print("- /release - Liberar jogador")
        print("- /players - Listar jogadores de um time")
        print("- /setmanager - Definir manager de time (admin)")
        print("- /removemanager - Remover manager de time (admin)")
        print("- /clubs - Ver todos os times e managers (admin)")
        print("- /openall - Abrir todos os sistemas (admin)")
        print("- /closeall - Fechar todos os sistemas (admin)")
        print("- /recommend - recomenda algum jogador")
        print("\n💾 Sistema de persistência de dados ATIVADO!")
        print("📁 Dados serão salvos automaticamente em 'rfo_data.json'")
        print("🔄 Bot lembrará o estado entre reinicializações")
        print("\nBot iniciando...")
        bot.run(token)