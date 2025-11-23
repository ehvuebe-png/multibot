const { Telegraf } = require('telegraf');

const tokens = [
 "7525940881:AAHOwB69-Iiku5m_F0unGRROr-6suZYmHGM",
 "8537687387:AAGkmQKbderww-iNlZE0Gyf2SO_0Beslugk",
 "8516563029:AAHzBLkrLM3QH__IxacyDkAoocG5zZZnTXs",
 "8470961208:AAFsigYqFZ6nuyDW4wdvIVqjIbOuePpl9FQ",
 "8592926668:AAEG9CVPJVYk4QnhQ7AHK1I8Fa5mJklt4aA",
 "8282249419:AAGPJNE0Y73bH-i5p6T1uzL7-H2S8HtmVEg"
];

tokens.forEach((token, index) => {
    const bot = new Telegraf(token);
    const id = index + 1;

    bot.start((ctx) => ctx.reply(`Bot ${id} đã hoạt động!\nGõ /menu`));

    bot.command("menu", (ctx) =>
        ctx.reply(`📌 MENU BOT ${id}\n\n1. /ping – kiểm tra bot sống`)
    );

    bot.command("ping", (ctx) => ctx.reply(`Bot ${id} OK 😎`));

    bot.launch()
        .then(() => console.log(`BOT ${id} ĐÃ CHẠY`))
        .catch(err => console.log(`Lỗi BOT ${id} →`, err));
});

// Giữ bot sống trên Render
setInterval(() => {}, 1000);
