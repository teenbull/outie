import os
import fnmatch

# Название итогового файла
OUTPUT_FILE = 'output.txt'

# Базовые исключения (на случай, если файлов ignore нет, чтобы скрипт не завис на мусоре)
DEFAULT_IGNORE = {'.git', '.idea', '__pycache__', 'dist', 'build', 'node_modules', '.outignore', '.gitignore'}

def load_ignore_patterns(base_dir):
    """
    Загружает правила игнорирования из .gitignore и .outignore.
    Возвращает объединенный список паттернов.
    """
    patterns = set(DEFAULT_IGNORE)
    
    for ignore_file in ['.gitignore', '.outignore']:
        path = os.path.join(base_dir, ignore_file)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Игнорируем пустые строки и комментарии
                    if line and not line.startswith('#'):
                        patterns.add(line)
                        
    return list(patterns)

def is_ignored(rel_path, patterns, is_dir=False):
    """
    Проверяет, попадает ли путь под правила игнорирования (аналог поведения git).
    """
    # Нормализуем путь для единообразия (прямые слеши для fnmatch)
    rel_path = rel_path.replace(os.sep, '/')
    parts = rel_path.split('/')

    for pattern in patterns:
        # Пропускаем инвертированные правила (!pattern) для простоты реализации
        if pattern.startswith('!'):
            continue

        # Определяем специфику паттерна
        is_root_pattern = pattern.startswith('/')
        clean_pattern = pattern.lstrip('/')
        
        only_dir = clean_pattern.endswith('/')
        clean_pattern = clean_pattern.rstrip('/')

        # Если паттерн только для папок (заканчивается на /), а мы проверяем файл - пропускаем
        if only_dir and not is_dir:
            continue

        if not is_root_pattern and '/' not in clean_pattern:
            # Паттерн вида "node_modules" или "*.txt" - ищем совпадение в любом компоненте пути
            if any(fnmatch.fnmatch(part, clean_pattern) for part in parts):
                return True
        else:
            # Паттерн вида "/build" или "src/*.py" - сопоставляем с полным относительным путем
            if fnmatch.fnmatch(rel_path, clean_pattern) or \
               fnmatch.fnmatch(rel_path, clean_pattern + '/*'):
                return True
                
    return False

def format_size(size_in_bytes):
    """Форматирует размер файла в удобочитаемый вид."""
    if size_in_bytes < 1024:
        return f"{size_in_bytes} Б"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.2f} КБ"
    else:
        return f"{size_in_bytes / (1024 * 1024):.2f} МБ"

def main():
    # Получаем путь к папке, в которой лежит сам этот скрипт
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(base_dir, OUTPUT_FILE)
    script_name = os.path.basename(__file__)

    # Загружаем правила игнорирования
    ignore_patterns = load_ignore_patterns(base_dir)

    # Счетчики статистики
    files_collected = 0
    total_lines = 0

    # Открываем итоговый файл для записи
    with open(output_path, 'w', encoding='utf-8') as outfile:
        
        # os.walk проходит по всем папкам и подпапкам
        for root, dirs, files in os.walk(base_dir):
            
            # Фильтруем папки на лету, чтобы не сканировать содержимое игнорируемых директорий
            valid_dirs =[]
            for d in dirs:
                dir_rel_path = os.path.relpath(os.path.join(root, d), base_dir)
                if not is_ignored(dir_rel_path, ignore_patterns, is_dir=True):
                    valid_dirs.append(d)
            dirs[:] = valid_dirs  # Перезаписываем список папок для os.walk
            
            for file in files:
                # Пропускаем сам скрипт и итоговый файл
                if file == OUTPUT_FILE or file == script_name:
                    continue
                
                filepath = os.path.join(root, file)
                relative_path = os.path.relpath(filepath, base_dir)
                
                # Проверяем файл по правилам игнорирования
                if is_ignored(relative_path, ignore_patterns, is_dir=False):
                    continue
                
                try:
                    # Пытаемся прочитать файл как текст (utf-8)
                    with open(filepath, 'r', encoding='utf-8') as infile:
                        content = infile.read()
                    
                    # Формируем блоки текста для записи
                    header = f"---------- File: {relative_path} ----------\n\n"
                    footer = f"\n---------- EOF: {relative_path} ----------\n\n\n"
                    
                    # Записываем всё в файл и одновременно считаем строки (\n)
                    outfile.write(header)
                    total_lines += header.count('\n')
                    
                    outfile.write(content)
                    total_lines += content.count('\n')
                    
                    # Если файл не заканчивается переносом строки, добавляем его
                    if not content.endswith('\n'):
                        outfile.write('\n')
                        total_lines += 1
                        
                    outfile.write(footer)
                    total_lines += footer.count('\n')
                    
                    # Увеличиваем счетчик обработанных файлов
                    files_collected += 1
                    
                except UnicodeDecodeError:
                    # Если файл не читается как текст (например, это картинка .png)
                    print(f"Пропущен нетекстовый/бинарный файл: {relative_path}")
                except Exception as e:
                    print(f"Ошибка при чтении файла {relative_path}: {e}")

    # Вычисляем итоговый размер созданного файла
    final_size_bytes = os.path.getsize(output_path)
    
    # Вывод результатов
    print("\n" + "="*45)
    print("Готово!")
    print(f"Все файлы ({files_collected} шт.) собраны в {OUTPUT_FILE}")
    print(f"Количество строк: {total_lines}")
    print(f"Размер файла:     {format_size(final_size_bytes)}")
    print("="*45)

if __name__ == '__main__':
    main()