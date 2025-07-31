import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ChatMemberStatus
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID

BLACKLIST_FILE = "blacklist.txt"
ALLOWED_GROUPS_FILE = "allowed_groups.txt"

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

# --- Tambahkan grup ke daftar grup yang diizinkan ---
@app.on_message(filters.command("addgrup") & filters.user(OWNER_ID))
async def add_grup(_, msg: Message):
    if not msg.chat or msg.chat.type not in ["group", "supergroup"]:
        return await msg.reply("❌ Perintah ini hanya dapat digunakan di dalam grup.", quote=True)

    group_id = msg.chat.id
    allowed = load_allowed_groups()
    if group_id in allowed:
        return await msg.reply("✅ Grup ini sudah terdaftar.", quote=True)

    allowed.append(group_id)
    save_allowed_groups(allowed)
    await msg.reply(f"✅ Grup `{group_id}` berhasil ditambahkan ke daftar yang diizinkan.", quote=True)

# --- Hapus pesan broadcast & blacklist ---
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
@app.on_message(filters.command("addblacklist"))
async def add_blacklist(_, msg: Message):
    if not is_group_allowed(msg.chat.id):
        return
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
    if not is_group_allowed(msg.chat.id):
        return
    if not await is_admin(msg.from_user.id, msg.chat.id):
        return
    if len(msg.command) < 2:
        return await msg.reply("Gunakan format: `/delblacklist kata1 kata2 ...`", quote=True)

    words = load_blacklist()
    to_remove = [w.lower() for w in msg.command[1:]]
    updated = [w for w in words if w not in to_remove]
    save_blacklist(updated)
    await msg.reply(f"❌ Dihapus dari blacklist:\n`{', '.join(to_remove)}`", quote=True)

# --- Lihat blacklist dengan inline button ---
@app.on_message(filters.command("listblacklist"))
async def list_blacklist(_, msg: Message):
    if not is_group_allowed(msg.chat.id):
        return
    if not await is_admin(msg.from_user.id, msg.chat.id):
        return

    words = load_blacklist()
    if not words:
        return await msg.reply("📭 Blacklist kosong.", quote=True)

    buttons = []
    row = []
    for i, word in enumerate(words):
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

# --- Tanggapi tombol inline ---
@app.on_callback_query(filters.regex("^bl_"))
async def on_blacklist_button(_, callback: CallbackQuery):
    word = callback.data.replace("bl_", "")
    await callback.answer(f"🔘 Kata: {word}", show_alert=True)

app.run()
