import bcrypt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码

    Args:
        plain_password: 前端已经做过 SHA256 的密码
        hashed_password: 数据库中存储的 bcrypt 哈希

    Returns:
        bool: 如果密码匹配返回 True，否则返回 False
    """
    # 将两个密码都编码为 UTF-8，并使用 bcrypt.checkpw() 进行比较
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """对密码进行哈希

    Args:
        password: 前端已经做过 SHA256 的密码

    Returns:
        str: bcrypt 哈希后的密码字符串（UTF-8编码）
    """
    # 生成随机 salt
    salt = bcrypt.gensalt()
    # 对密码进行哈希，并解码为 UTF-8 字符串返回
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
