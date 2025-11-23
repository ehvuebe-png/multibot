const { Telegraf } = require("telegraf");

const tokens = [
  "7525940881:AAHOwB69-Iiku5m_F0unGRROr-6suZYmHGM",
  "8537687387:AAGkmQKbderww-iNlZE0Gyf2SO_0Beslugk",
  "8516563029:AAHzBLkrLM3QH__IxacyDkAoocG5zZZnTXs",
  "8470961208:AAFsigYqFZ6nuyDW4wdvIVqjIbOuePpl9FQ",
  "8592926668:AAEG9CVPJVYk4QnhQ7AHK1I8Fa5mMkklt4aA",
  "8282249419:AAGPJNE0Y73bH-i5p6T1uzL7-H2S8HtmVEg"
];

tokens.forEach((token, index) => {
  const bot = new Telegraf(token);

  bot.start((ctx) =>
    ctx.reply(`BOT ${index + 1} ĐÃ HOẠT ĐỘNG!`)
  );

  bot.hears("menu", (ctx) =>
    ctx.reply(`Menu của BOT ${index + 1}`)
  );

  bot.launch();
  console.log(`BOT ${index + 1} đã chạy`);
});

// Giữ server sống trên Render
require("http")
  .createServer((_, res) => res.end("Bot is running"))
  .listen(process.env.PORT || 3000);
