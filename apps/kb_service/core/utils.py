from apps.kb_service.core.config import kb_settings


def parse_size(size_str):
    """
    解析大小字符串，支持多种格式：
    - 字节数: "1048576"
    - 带单位: "1M", "1MB", "1m", "1mb", "1MiB", "1KiB" 等

    Args:
        size_str: 大小字符串

    Returns:
        int: 字节数

    Raises:
        ValueError: 当格式不正确时
    """
    if isinstance(size_str, int):
        return size_str

    size_str = str(size_str).strip()

    # 如果是纯数字，直接返回
    if size_str.isdigit():
        return int(size_str)

    # 定义单位映射
    units = {
        'B': 1,
        'K': 1024,
        'M': 1024 ** 2,
        'G': 1024 ** 3,
        'T': 1024 ** 4,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4,
        'KIB': 1024,
        'MIB': 1024 ** 2,
        'GIB': 1024 ** 3,
        'TIB': 1024 ** 4,
    }

    # 提取数字部分和单位部分
    size_str = size_str.upper()
    for unit in sorted(units.keys(), key=len, reverse=True):
        if size_str.endswith(unit):
            number_part = size_str[:-len(unit)]
            if number_part.replace('.', '', 1).isdigit():
                number = float(number_part)
                return int(number * units[unit])

    # 尝试解析不带B的单位 (K, M, G, T)
    for unit in ['K', 'M', 'G', 'T']:
        if size_str.endswith(unit):
            number_part = size_str[:-len(unit)]
            if number_part.replace('.', '', 1).isdigit():
                number = float(number_part)
                return int(number * units[unit])

    # 如果都无法解析，抛出异常
    raise ValueError(f"无法解析大小格式: {size_str}")


def get_queue_size_threshold():
    """
    从配置获取队列大小阈值，支持多种格式

    Returns:
        int: 队列大小阈值（字节）
    """
    threshold = kb_settings.QUEUE_SIZE_THRESHOLD
    try:
        return parse_size(threshold)
    except ValueError:
        return int(threshold)