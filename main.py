import os
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    TOKEN = os.getenv("8529986932:AAG3xWEc1kmDpsItBXB6geMIODG-a59AMUk") 

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Отправляет приветственное сообщение при команде /start."""
        user = update.effective_user
        await update.message.reply_html(
            f"Привет, {user.mention_html()}! Я бот для Доты 2. Пока что я только учусь, но скоро буду анализировать твои игры!",
            # reply_markup=ForceReply(selective=True), # Это если хочешь, чтобы бот отвечал на конкретное сообщение
        )

    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Отправляет сообщение с помощью при команде /help."""
        await update.message.reply_text("Я пока ничего не умею, но скоро научусь! Жди обновлений.")

    async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Эхо-ответ на любое текстовое сообщение."""
        await update.message.reply_text(f"Ты сказал: '{update.message.text}'? Я пока не понимаю, но скоро буду!")

   
