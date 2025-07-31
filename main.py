import os
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID

BLACKLIST_FILE = "blacklist.txt"

app = Client("filter_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- Fungsi bantu ---
def load_blacklist():
    if not os.path.exists(BLACKLIST_FILE):
        return []
    with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
        return [line.strip().lower() for line in f if line.strip()]

def save_blacklist(words):
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        for word in sorted(set(words)):
            f.write(f"{word}\n")

async def is_admin(user_id: int, chat_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    try:
        member = await app.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except:
        return False

# --- Hapus pesan broadcast & blacklist ---
@app.on_message(filters.group)
async def filter_messages(_, msg: Message):
    if msg.forward_from or msg.forward_from_chat:
        try:
            await msg.delete()
            return
        except:
            pass

    if msg.text:
        text = msg.text.lower()
        for word in load_blacklist():
            if word in text:
                try:
                    await msg.delete()
                    return
                except:
                    pass

# --- Tambah blacklist ---
@app.on_message(filters.command("addblacklist"))
async def add_blacklist(_, msg: Message):
    if not await is_admin(msg.from_user.id, msg.chat.id):
        return
    if len(msg.command) < 2:
        return await msg.reply("Gunakan format: `/addblacklist kata1 kata2 ...`", quote=True)

    words = load_blacklist()
    new_words = msg.command[1:]
    words.extend(w.lower() for w in new_words if w.lower() not in words)
    save_blacklist(words)
    await msg.reply(f"✅ Ditambahkan ke blacklist:\n`{', '.join(new_words)}`", quote=True)

# --- Hapus dari blacklist ---
@app.on_message(filters.command("delblacklist"))
async def del_blacklist(_, msg: Message):
    if not await is_admin(msg.from_user.id, msg.chat.id):
        return
    if len(msg.command) < 2:
        return await msg.reply("Gunakan format: `/delblacklist kata1 kata2 ...`", quote=True)

    words = load_blacklist()
    to_remove = [w.lower() for w in msg.command[1:]]
    updated = [w for w in words if w not in to_remove]
    save_blacklist(updated)
    await msg.reply(f"❌ Dihapus dari blacklist:\n`{', '.join(to_remove)}`", quote=True)

# --- Lihat blacklist ---
@app.on_message(filters.command("listblacklist"))
async def list_blacklist(_, msg: Message):
    if not await is_admin(msg.from_user.id, msg.chat.id):
        return
    words = load_blacklist()
    if not words:
        await msg.reply("📭 Blacklist kosong.", quote=True)
    else:
        await msg.reply("📌 Daftar blacklist:\n" + "\n".join(f"- {w}" for w in words), quote=True)

app.run()
