import { Telegraf } from "telegraf";

const TOKENS = [
  "8282249419:AAGPJNE0Y73bH-i5p6T1uzL7-H2S8HtmVEg",
  "7525940881:AAHOwB69-Iiku5m_F0unGRROr-6suZYmHGM",
  "8537687387:AAGkmQKbderww-iNlZE0Gyf2SO_0Beslugk",
  "8516563029:AAHzBLkrLM3QH__IxacyDkAoocG5zZZnTXs",
  "8592926668:AAEG9CVPJVYk4QnhQ7AHK1I8Fa5mJklt4aA",
  "8470961208:AAFsigYqFZ6nuyDW4wdvIVqjIbOuePpl9FQ"
];

function runBot(token) {
  const bot = new Telegraf(token);

  bot.start((ctx) =>
    ctx.reply("Bots đang hoạt động ✅\nMenu:\n /help\n /start")
  );

  bot.help((ctx) => ctx.reply("Lệnh hỗ trợ:\n/start\n/help"));

  bot.on("text", (ctx) => {
    ctx.reply("Bot đang phản hồi tin nhắn của bạn 💬");
  });

  bot.launch().then(() => {
    console.log("Bot chạy:", token);
  });

  return bot;
}

TOKENS.forEach((token) => {
  try {
    runBot(token);
  } catch (e) {
    console.log("Lỗi bot:", token, e);
  }
});

process.once("SIGINT", () => process.exit(0));
process.once("SIGTERM", () => process.exit(0));
