const { Telegraf } = require("telegraf");
const fs = require("fs");

// ======================
// 6 TOKEN BOT CỦA BẠN
// ======================
const BOT_TOKENS = [
  "7525940881:AAHOwB69-Iiku5m_F0unGRROr-6suZYmHGM",
  "8537687387:AAGkmQKbderww-iNlZE0Gyf2SO_0Beslugk",
  "8516563029:AAHzBLkrLM3QH__IxacyDkAoocG5zZZnTXs",
  "8470961208:AAFsigYqFZ6nuyDW4wdvIVqjIbOuePpl9FQ",
  "8592926668:AAEG9CVPJVYk4QnhQ7AHK1I8Fa5mJklt4aA",
  "8282249419:AAGPJNE0Y73bH-i5p6T1uzL7-H2S8HtmVEg"
];
// ======================

// TEXT MENU
const menuText = `
🔥 MENU BOT
/spam — spam war.txt
/spam @tag — spam có tag
/setdelay X — đổi delay
/setuser @tag — đổi tag
/stop — dừng spam
`;

// HÀM TẠO BOT
function createBot(token, botName) {
  const bot = new Telegraf(token);
  let isSpamming = false;
  let delay = 0;
  let tagUser = "@tag";

  bot.start((ctx) => {
    ctx.reply(`🤖 Bot ${botName} đã hoạt động!\nGõ /menu để xem lệnh.`);
  });

  bot.command("menu", (ctx) => {
    ctx.reply(
      `📌 MENU BOT ${botName}\n` +
      menuText +
      `\n⏱ Delay: ${delay}s\n🏷 Tag: ${tagUser}`
    );
  });

  bot.command("setdelay", (ctx) => {
    const args = ctx.message.text.split(" ");
    if (!args[1]) return ctx.reply("❗ Nhập delay");
    delay = Number(args[1]);
    ctx.reply(`⏱ Delay đổi thành: ${delay}s`);
  });

  bot.command("setuser", (ctx) => {
    const args = ctx.message.text.split(" ");
    if (!args[1]) return ctx.reply("❗ Nhập tag");
    tagUser = args[1];
    ctx.reply(`🏷 Tag đổi thành: ${tagUser}`);
  });

  bot.command("stop", (ctx) => {
    isSpamming = false;
    ctx.reply("🛑 Đã dừng spam");
  });

  bot.command("spam", async (ctx) => {
    if (isSpamming) return ctx.reply("❗ Bot đang spam rồi!");

    isSpamming = true;

    let text = "";
    try {
      text = fs.readFileSync("war.txt", "utf8");
    } catch (e) {
      return ctx.reply("❌ Không tìm thấy file war.txt");
    }

    ctx.reply("🔥 Bắt đầu spam!");

    while (isSpamming) {
      await ctx.reply(`${tagUser}\n${text}`);
      await new Promise(resolve => setTimeout(resolve, delay * 1000));
    }
  });

  bot.launch();
  console.log(`BOT ${botName} ĐÃ CHẠY`);
}

// Chạy tất cả bot
BOT_TOKENS.forEach((token, index) => {
  createBot(token, `BOT${index + 1}`);
});
