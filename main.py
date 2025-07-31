import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ChatMemberStatus
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID

# Gunakan path absolut agar file selalu disimpan & dibaca dari lokasi script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BLACKLIST_FILE = os.path.join(BASE_DIR, "blacklist.txt")
ALLOWED_GROUPS_FILE = os.path.join(BASE_DIR, "allowed_groups.txt")

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

def load_allowed_groups():
    if not os.path.exists(ALLOWED_GROUPS_FILE):
        return []
    with open(ALLOWED_GROUPS_FILE, "r", encoding="utf-8") as f:
        return [int(line.strip()) for line in f if line.strip().isdigit()]

def save_allowed_groups(group_ids):
    with open(ALLOWED_GROUPS_FILE, "w", encoding="utf-8") as f:
        for gid in sorted(set(group_ids)):
            f.write(f"{gid}\n")

def is_group_allowed(group_id: int) -> bool:
    return group_id in load_allowed_groups()

async def is_admin(user_id: int, chat_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    try:
        member = await app.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except:
        return False

# --- Tambah grup ---
@app.on_message(filters.command("addgrup"))
async def add_grup(_, msg: Message):
    if msg.chat.type != "supergroup" and msg.chat.type != "group":
        return await msg.reply("❌ Perintah ini hanya dapat digunakan di dalam grup.", quote=True)

    if msg.from_user.id != OWNER_ID:
        return

    group_id = msg.chat.id
    allowed = load_allowed_groups()
    if group_id in allowed:
        return await msg.reply("✅ Grup ini sudah terdaftar.", quote=True)
    allowed.append(group_id)
    save_allowed_groups(allowed)
    await msg.reply(f"✅ Grup `{group_id}` berhasil ditambahkan ke daftar yang diizinkan.", quote=True)

# --- Hapus grup ---
@app.on_message(filters.command("removegrup"))
async def remove_grup(_, msg: Message):
    if msg.chat.type != "supergroup" and msg.chat.type != "group":
        return await msg.reply("❌ Perintah ini hanya dapat digunakan di dalam grup.", quote=True)

    if msg.from_user.id != OWNER_ID:
        return

    group_id = msg.chat.id
    allowed = load_allowed_groups()
    if group_id not in allowed:
        return await msg.reply("⚠️ Grup ini belum terdaftar.", quote=True)
    allowed.remove(group_id)
    save_allowed_groups(allowed)
    await msg.reply(f"❌ Grup `{group_id}` telah dihapus dari daftar yang diizinkan.", quote=True)

# --- List grup ---
@app.on_message(filters.command("listgrup") & filters.user(OWNER_ID))
async def list_grup(_, msg: Message):
    groups = load_allowed_groups()
    if not groups:
        return await msg.reply("📭 Tidak ada grup yang terdaftar.", quote=True)
    text = "\n".join(f"- `{gid}`" for gid in groups)
    await msg.reply(f"📌 Daftar grup yang diizinkan:\n{text}", quote=True)

# --- Filter pesan broadcast & blacklist ---
@app.on_message(filters.group)
async def filter_messages(_, msg: Message):
    if not is_group_allowed(msg.chat.id):
        return
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
@app.on_message(filters.command("addblacklist") & filters.group)
async def add_blacklist(_, msg: Message):
    if not is_group_allowed(msg.chat.id) or not await is_admin(msg.from_user.id, msg.chat.id):
        return
    if len(msg.command) < 2:
        return await msg.reply("Gunakan format: `/addblacklist kata1 kata2 ...`", quote=True)
    words = load_blacklist()
    new_words = [w.lower() for w in msg.command[1:] if w.lower() not in words]
    if not new_words:
        return await msg.reply("⚠️ Tidak ada kata baru untuk ditambahkan.", quote=True)
    words.extend(new_words)
    save_blacklist(words)
    await msg.reply(f"✅ Ditambahkan ke blacklist: `{', '.join(new_words)}`", quote=True)

# --- Hapus blacklist ---
@app.on_message(filters.command("delblacklist") & filters.group)
async def del_blacklist(_, msg: Message):
    if not is_group_allowed(msg.chat.id) or not await is_admin(msg.from_user.id, msg.chat.id):
        return
    if len(msg.command) < 2:
        return await msg.reply("Gunakan format: `/delblacklist kata1 kata2 ...`", quote=True)
    words = load_blacklist()
    to_remove = [w.lower() for w in msg.command[1:]]
    updated = [w for w in words if w not in to_remove]
    save_blacklist(updated)
    await msg.reply(f"❌ Dihapus dari blacklist: `{', '.join(to_remove)}`", quote=True)

# --- List blacklist ---
@app.on_message(filters.command("listblacklist") & filters.group)
async def list_blacklist(_, msg: Message):
    if not is_group_allowed(msg.chat.id) or not await is_admin(msg.from_user.id, msg.chat.id):
        return
    words = load_blacklist()
    if not words:
        return await msg.reply("📭 Blacklist kosong.", quote=True)
    buttons, row = [], []
    for word in words:
        row.append(InlineKeyboardButton(word, callback_data=f"bl_{word}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    await msg.reply(
        "📌 Daftar blacklist (klik untuk info):",
        reply_markup=InlineKeyboardMarkup(buttons),
        quote=True
    )

# --- Callback blacklist ---
@app.on_callback_query(filters.regex(r"^bl_"))
async def on_blacklist_button(_, callback: CallbackQuery):
    word = callback.data.split("bl_")[1]
    await callback.answer(f"🔘 Kata: {word}", show_alert=True)

app.run()
