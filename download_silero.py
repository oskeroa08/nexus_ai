
"""Скрипт для скачивания Silero модели локально для встраивания в EXE."""

import os
import torch


def main():
    # Создаём папку для модели
    model_dir = os.path.join(os.path.dirname(__file__), "assets", "silero")
    os.makedirs(model_dir, exist_ok=True)
    
    print("Скачиваем Silero модель...")
    
    try:
        # Скачиваем модель (это сохранит её в кэш torch.hub, потом мы скопируем)
        result = torch.hub.load(
            repo_or_dir="snakers4/silero-models",
            model="silero_tts",
            language="ru",
            speaker="v5_5_ru",
            trust_repo=True
        )
        
        # Получаем путь к кэшу torch.hub
        hub_dir = torch.hub.get_dir()
        silero_cache = os.path.join(hub_dir, "snakers4_silero-models_master")
        
        print(f"Кэш Silero найден в: {silero_cache}")
        
        # Копируем всё из кэша в наш assets/silero
        import shutil
        
        if os.path.exists(silero_cache):
            for item in os.listdir(silero_cache):
                src = os.path.join(silero_cache, item)
                dst = os.path.join(model_dir, item)
                if os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            print(f"Модель успешно скопирована в {model_dir}!")
        else:
            print("Не удалось найти кэш Silero!")
            
        print("\nГотово! Модель Silero теперь в папке assets/silero")
        
    except Exception as e:
        print(f"Ошибка при скачивании: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
