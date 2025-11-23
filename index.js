const { Telegraf } = require("telegraf");
const fs = require("fs");

// ==================== CONFIG ====================
const TOKENS = [
  "8470961208:AAGfEuFp8YYhDevvQTrAZKO3Bci60nygGno",
  "8516563029:AAEh_n_m8dQodpIwqrxfvfO-uQbqaM6c148",
  "7525940881:AAGLlOQEE8W1WmRiXtiUlPuzwpBgcMPGA4k",
  "8282249419:AAFmsoqmiR005ODtCiFoDiQeXjFZjxyYXfU",
  "8537687387:AAE4eSA-svj_JEyaR3ZEiJmbNlrrXVjvcd8",
  "8592926668:AAEJNY1JVcWzCi0_X4FbByh9zj6brkaPYec"
];

const ADMIN_FILE = "admins.txt";
const WAR_FILE = "war.txt";

// Delay mặc định + tag mặc định
let currentDelay = 0;
let currentTag = "@default";

// Stop flag cho tất cả bot
let stopFlag = false;

// ==================== FILE SYSTEM ====================
function loadAdmins() {
  if (!fs.existsSync(ADMIN_FILE)) fs.writeFileSync(ADMIN_FILE, "");
  return fs.readFileSync(ADMIN_FILE, "utf8")
    .split("\n")
    .filter(x => x.trim());
}

function addAdmin(id) {
  fs.appendFileSync(ADMIN_FILE, id + "\n");
}

function removeAdmin(id) {
  let arr = loadAdmins();
  arr = arr.filter(x => x !== id);
  fs.writeFileSync(ADMIN_FILE, arr.join("\n"));
}

function loadWar() {
  if (!fs.existsSync(WAR_FILE)) return [];
  return fs.readFileSync(WAR_FILE, "utf8")
    .split("\n")
    .filter(x => x.trim());
}

// ==================== MENU TEXT ====================
function menuText() {
  return `
🔥 <b>MENU ĐIỀU KHIỂN</b>

📌 <b>SPAM</b>
/spam – spam ngẫu nhiên war.txt  
/spam @user – spam kèm tag  
/stop – dừng spam  

⚙ <b>CÀI ĐẶT</b>
/setdelay X – delay hiện tại: <b>${currentDelay}s</b>  
/settag @abc – tag mặc định: <b>${currentTag}</b>  

📄 <b>TỆP</b>
/war – xem war.txt  
/groupid – xem ID nhóm  

👑 <b>ADMIN</b>
/admins – xem danh sách admin  
/addadmin ID  
/deladmin ID  
`;
}

// ==================== SPAM FUNCTION ====================
async function spam(bot, chatId, tag) {
  stopFlag = false;
  const war = loadWar();

  if (war.length === 0) {
    return bot.telegram.sendMessage(chatId, "⚠ war.txt đang trống.");
  }

  await bot.telegram.sendMessage(chatId, `🚀 Bắt đầu spam...\nTag: ${tag}\nDelay: ${currentDelay}s`);

  while (!stopFlag) {
    const line = war[Math.random() * war.length | 0];
    const text = `${tag} ${line}`;

    try {
      await bot.telegram.sendMessage(chatId, text);
    } catch {}

    if (currentDelay > 0) {
      await new Promise(r => setTimeout(r, currentDelay * 1000));
    }
  }

  bot.telegram.sendMessage(chatId, "🛑 Đã dừng spam.");
}

// ==================== TẠO BOT ====================
TOKENS.forEach((token, index) => {
  const bot = new Telegraf(token);
  const botNumber = index + 1;

  function isAdmin(id) {
    return loadAdmins().includes(id.toString());
  }

  // ===== /start =====
  bot.start((ctx) => {
    ctx.reply(`BOT ${botNumber} đã hoạt động ✔\nGõ /menu để xem lệnh`);
  });

  // ===== /menu =====
  bot.command("menu", (ctx) => {
    if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Bạn không có quyền.");
    ctx.reply(menuText(), { parse_mode: "HTML" });
  });

  // ===== /spam =====
  bot.command("spam", (ctx) => {
    if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Không có quyền.");

    const parts = ctx.message.text.split(" ");
    let tag = currentTag;

    if (parts[1] && parts[1].startsWith("@")) tag = parts[1];

    spam(bot, ctx.chat.id, tag);
  });

  // ===== /stop =====
  bot.command("stop", (ctx) => {
    if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Không có quyền.");
    stopFlag = true;
    ctx.reply("🛑 Đang dừng spam...");
  });

  // ===== /setdelay =====
  bot.command("setdelay", (ctx) => {
    if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Không có quyền.");

    const parts = ctx.message.text.split(" ");
    if (!parts[1]) return ctx.reply("❌ Sai cú pháp. Ví dụ: /setdelay 0.2");

    currentDelay = Math.max(0, parseFloat(parts[1]));
    ctx.reply(`⏱ Delay đổi thành: ${currentDelay}s`);
  });

  // ===== /settag =====
  bot.command("settag", (ctx) => {
    if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Không có quyền.");

    const parts = ctx.message.text.split(" ");
    if (!parts[1] || !parts[1].startsWith("@"))
      return ctx.reply("❌ Tag phải bắt đầu bằng @");

    currentTag = parts[1];
    ctx.reply(`✅ Tag mặc định: ${currentTag}`);
  });

  // ===== /groupid =====
  bot.command("groupid", (ctx) => {
    ctx.reply(`🆔 Group ID: <code>${ctx.chat.id}</code>`, { parse_mode: "HTML" });
  });

  // ===== /admins =====
  bot.command("admins", (ctx) => {
    if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Không có quyền.");

    const list = loadAdmins().join("\n") || "(trống)";
    ctx.reply(`👑 DANH SÁCH ADMIN:\n${list}`);
  });

  // ===== /addadmin =====
  bot.command("addadmin", (ctx) => {
    if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Không có quyền.");

    const parts = ctx.message.text.split(" ");
    if (!parts[1]) return ctx.reply("❌ Sai cú pháp: /addadmin 12345");

    addAdmin(parts[1]);
    ctx.reply(`✅ Đã thêm admin: ${parts[1]}`);
  });

  // ===== /deladmin =====
  bot.command("deladmin", (ctx) => {
    if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Không có quyền.");

    const parts = ctx.message.text.split(" ");
    if (!parts[1]) return ctx.reply("❌ Sai cú pháp: /deladmin 12345");

    removeAdmin(parts[1]);
    ctx.reply(`❌ Đã xoá admin: ${parts[1]}`);
  });

  bot.launch();
  console.log(`BOT ${botNumber} đã chạy ✔`);
});

console.log("🔥 TẤT CẢ 6 BOT ĐÃ KHỞI ĐỘNG ✔");
