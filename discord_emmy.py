import os
import discord
import asyncio
import uuid
import ollama # <-- BUTUH INI BUAT VISION
from dotenv import load_dotenv
from emmy_core import get_emmy_brain, qdrant_store, generate_voice_audio # <--- TAMBAH INI
# Kalau qdrant_store error, pastiin di emmy_core.py variable-nya ga di dalem fungsi

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 1. LOAD ENV (WAJIB DULUAN)
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
IP_WINDOWS_LU = "127.0.0.1" # Atau os.getenv("IP_WINDOWS_LU")

# 2. LOAD OTAK
agent = get_emmy_brain()

# 3. SETUP DISCORD
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True 
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'🔥 Emmy (Discord Body) Online as {client.user}')

@client.event
async def on_message(message):
    # Filter diri sendiri
    if message.author == client.user: return
    
    # Filter Mention/DM (Biar ga jadi spyware)
    is_mentioned = client.user in message.mentions
    is_dm = isinstance(message.channel, discord.DMChannel)
    
    # Kalau ga di-mention DAN bukan DM, cuekin
    if not (is_mentioned or is_dm): return
    
    # Bersihin input
    user_input = message.content.replace(f'<@{client.user.id}>', '').strip()
    if not user_input and not message.attachments: user_input = "Hello!" 

    # --- FITUR TAMBAHAN (MATA & MEMORI) ---
    system_addon = ""
    
    if message.attachments:
        for attachment in message.attachments:
            # A. HANDLE GAMBAR (VISION)
            if attachment.content_type and attachment.content_type.startswith('image'):
                await message.channel.send("👀 Looking at the image...")
                filename = f"img_{uuid.uuid4()}.jpg"
                await attachment.save(filename)
                try:
                    async with message.channel.typing():
                        # Pake Client Ollama langsung buat Vision
                        client_vision = ollama.Client(host=f"http://{IP_WINDOWS_LU}:11434")
                        res = await asyncio.to_thread(client_vision.chat, 
                            model='moondream', # Pastikan udah pull moondream
                            messages=[{'role': 'user', 'content': 'Describe this image.', 'images': [filename]}]
                        )
                        system_addon += f"\n[IMAGE CONTEXT: {res['message']['content']}]"
                except Exception as e: 
                    print(f"Vision error: {e}")
                finally: 
                    if os.path.exists(filename): os.remove(filename)
            
            # B. HANDLE PDF (RAG)
            elif attachment.content_type == 'application/pdf':
                await message.channel.send("📚 Reading document... Give me a moment, Darling.")
                filename = f"doc_{uuid.uuid4()}.pdf"
                await attachment.save(filename)
                
                try:
                    async with message.channel.typing():
                        # Baca PDF
                        loader = PyPDFLoader(filename)
                        docs = await asyncio.to_thread(loader.load)
                        
                        # Pecah Text
                        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                        splits = text_splitter.split_documents(docs)
                        
                        # Masukin ke Qdrant (Panggil dari emmy_core)
                        await asyncio.to_thread(qdrant_store.add_documents, splits)
                        
                        system_addon += f"\n[SYSTEM: I have read the PDF document '{attachment.filename}'. Content is now in my memory.]"
                        await message.channel.send(f"✅ I've finished reading **{attachment.filename}**. What would you like to know about it?")
                        
                except Exception as e:
                    await message.channel.send(f"❌ Failed to read PDF: {e}")
                finally:
                    if os.path.exists(filename): os.remove(filename)
            
            # C. HANDLE AUDIO (VOICE RESPONSE)
            

    # Gabung Context
    final_prompt = user_input + system_addon
    print(f"📩 Discord Input: {final_prompt[:50]}...")

    # EXECUTE AGENT
    try:
        async with message.channel.typing():
            # Thread ID Unik buat Discord
            thread_id = f"discord_{message.author.id}_v6_my_bini_hdv"
            config = {"configurable": {"thread_id": thread_id}}
            
            # Panggil Otak
            response = await asyncio.to_thread(
                agent.invoke, 
                {"messages": [{"role": "user", "content": final_prompt}]}, 
                config
            )
            
            bot_reply = response['messages'][-1].content

            # Anti JSON Leak
            if bot_reply and ('"name":' in bot_reply or '{"' in bot_reply):
                print("⚠️ JSON LEAK DETECTED")
                bot_reply = "*smiles* I tried to calculate something but got confused. Let's just say I love you!"

            # --- BAGIAN BARU: KIRIM SUARA ---
            if bot_reply:
                # 1. Kirim Teks Dulu (Biar user bisa baca kalau males denger)
                if len(bot_reply) > 2000:
                    chunks = [bot_reply[i:i+1900] for i in range(0, len(bot_reply), 1900)]
                    for chunk in chunks:
                        await message.channel.send(chunk)
                else:
                    await message.channel.send(bot_reply)
                
                # 2. Generate & Kirim Audio (VN)
                # Kita limit biar ga generate novel (misal max 500 karakter buat suara)
                text_to_speak = bot_reply[:500] 
                
                # Jalanin di thread terpisah biar bot ga nge-freeze pas mikir suara
                audio_file = await asyncio.to_thread(generate_voice_audio, text_to_speak)
                
                if audio_file:
                    try:
                        # Kirim sebagai Voice Note
                        await message.channel.send(
                            file=discord.File(audio_file),
                            reference=message # Reply ke user
                        )
                    except Exception as e:
                        print(f"Gagal upload audio: {e}")
                    finally:
                        # Hapus file sampah
                        if os.path.exists(audio_file):
                            os.remove(audio_file)

    except Exception as e:
        print(f"❌ Agent Error: {e}")
        await message.channel.send("My circuits are overloaded. Please try again later.")

if __name__ == "__main__":
    if DISCORD_TOKEN:
        client.run(DISCORD_TOKEN)
    else:
        print("❌ ERROR: DISCORD_TOKEN gak kebaca dari .env!")