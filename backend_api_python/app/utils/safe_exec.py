"""
安全的代码执行工具
提供超时、资源限制和沙箱环境
"""
import sys
import os
import threading
import traceback
from typing import Dict, Any, Optional, Tuple

from app.utils.logger import get_logger

logger = get_logger(__name__)


class TimeoutError(Exception):
    """代码执行超时异常"""
    pass


def _async_raise(thread_id: int, exc_type: type) -> None:
    import ctypes
    if not thread_id:
        return
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(thread_id), ctypes.py_object(exc_type))
    if res == 0:
        raise ValueError("invalid thread id")
    if res != 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(thread_id), None)
        raise RuntimeError("PyThreadState_SetAsyncExc failed")


def run_with_timeout(func, args=(), kwargs=None, timeout_seconds=30):
    """
    使用后台线程执行函数，并在超时时尝试中断线程
    
    Args:
        func: 要执行的函数
        args: 位置参数
        kwargs: 关键字参数
        timeout_seconds: 超时时间（秒）
    """
    if kwargs is None:
        kwargs = {}
        
    result_container = []
    exception_container = []
    
    def target():
        try:
            res = func(*args, **kwargs)
            result_container.append(res)
        except Exception as e:
            # 捕获异常以便在主线程重新抛出
            exception_container.append(e)
            
    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout_seconds)
    
    if thread.is_alive():
        try:
            _async_raise(thread.ident or 0, TimeoutError)
        except Exception as e:
            logger.warning(f"Failed to interrupt thread on timeout: {e}")

        thread.join(1)
        if thread.is_alive():
            logger.warning("Timeout thread still running after interrupt attempt")
        raise TimeoutError(f"代码执行超时（超过{timeout_seconds}秒）")
        
    if exception_container:
        raise exception_container[0]
        
    return result_container[0] if result_container else None


def safe_exec_code(
    code: str,
    exec_globals: Dict[str, Any],
    exec_locals: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    max_memory_mb: Optional[int] = None
) -> Dict[str, Any]:
    """
    安全执行Python代码
    
    Args:
        code: 要执行的Python代码
        exec_globals: 全局变量字典
        exec_locals: 局部变量字典（如果为None，则使用exec_globals）
        timeout: 超时时间（秒），默认30秒
        max_memory_mb: 最大内存限制（MB），默认500MB
    
    Returns:
        执行结果字典，包含：
        - success: bool，是否执行成功
        - error: str，错误信息（如果失败）
        - result: Any，执行结果（如果有）
    
    Raises:
        TimeoutError: 如果代码执行超时
    """
    if exec_locals is None:
        exec_locals = exec_globals
    
    # 设置内存限制（如果支持）
    if max_memory_mb is None:
        max_memory_mb = 500  # 默认500MB
    
    try:
        # 注意：resource.setrlimit 是进程级别，会影响整个 API 进程。
        # 之前全局限制为 500MB 可能导致并行策略/线程无法分配内存。
        # 仅当显式开启 SAFE_EXEC_ENABLE_RLIMIT 时才设置。
        if sys.platform != 'win32' and os.getenv('SAFE_EXEC_ENABLE_RLIMIT', 'false').lower() == 'true':
            try:
                import resource
                max_memory_bytes = max_memory_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))
                logger.debug(f"Memory limit set: {max_memory_mb}MB (SAFE_EXEC_ENABLE_RLIMIT enabled)")
            except (ImportError, ValueError, OSError) as e:
                logger.warning(f"Failed to set memory limit: {str(e)}")
        else:
            logger.debug("No resource memory limit (SAFE_EXEC_ENABLE_RLIMIT disabled or unsupported platform)")
        
        # 使用跨平台的线程超时控制
        def do_exec():
            exec(code, exec_globals, exec_locals)
            
        run_with_timeout(do_exec, timeout_seconds=timeout)
        
        return {
            'success': True,
            'error': None,
            'result': None
        }
        
    except MemoryError as e:
        error_msg = f"代码执行内存不足（超过{max_memory_mb}MB限制）"
        logger.error(f"Code execution out of memory (limit={max_memory_mb}MB)")
        return {
            'success': False,
            'error': error_msg,
            'result': None
        }
    except TimeoutError as e:
        error_msg = str(e)
        logger.error(f"Code execution timed out (timeout={timeout}s)")
        return {
            'success': False,
            'error': error_msg,
            'result': None
        }
    except Exception as e:
        error_msg = f"代码执行错误: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"Code execution error: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': error_msg,
            'result': None
        }


def validate_code_safety(code: str) -> Tuple[bool, Optional[str]]:
    """
    验证代码安全性（基本检查）
    
    检查代码中是否包含危险的函数调用或导入
    
    Args:
        code: 要检查的Python代码
    
    Returns:
        (is_safe: bool, error_message: Optional[str])
    """
    import ast
    import re
    
    # 危险的关键字和函数名
    dangerous_patterns = [
        # 系统命令执行
        r'\bos\.system\b',
        r'\bos\.popen\b',
        r'\bos\.spawn\b',
        r'\bos\.exec\b',
        r'\bos\.fork\b',
        r'\bsubprocess\b',
        r'\bcommands\b',
        # 代码执行
        r'\b__import__\s*\(',
        r'\beval\s*\(',
        r'\bexec\s*\(',
        r'\bcompile\s*\(',
        # 文件操作
        r'\bopen\s*\(',
        r'\bfile\s*\(',
        r'\b__builtins__\b',
        # 模块导入
        r'\bimport\s+os\b',
        r'\bimport\s+sys\b',
        r'\bimport\s+subprocess\b',
        r'\bimport\s+pymysql\b',
        r'\bimport\s+sqlite3\b',
        r'\bimport\s+requests\b',
        r'\bimport\s+urllib\b',
        r'\bimport\s+http\b',
        r'\bimport\s+socket\b',
        r'\bimport\s+ftplib\b',
        r'\bimport\s+telnetlib\b',
        r'\bimport\s+pickle\b',
        r'\bimport\s+cpickle\b',
        r'\bimport\s+marshal\b',
        r'\bimport\s+ctypes\b',
        r'\bimport\s+multiprocessing\b',
        r'\bimport\s+threading\b',
        r'\bimport\s+concurrent\b',
        # 反射和元编程（可能用于绕过限制）
        r'\bgetattr\s*\(.*__import__',
        r'\bgetattr\s*\(.*eval',
        r'\bgetattr\s*\(.*exec',
        r'\bsetattr\s*\(',
        r'\b__getattribute__\b',
        r'\b__setattr__\b',
        r'\b__dict__\b',
        r'\bglobals\s*\(',
        r'\blocals\s*\(',
        r'\bdir\s*\(',
        r'\btype\s*\(.*\)\s*\(',  # type() 可能用于创建新类型
        r'\b__class__\b',
        r'\b__bases__\b',
        r'\b__subclasses__\b',
        r'\b__mro__\b',
        r'\b__init__\b.*__import__',
        r'\b__new__\b.*__import__',
        # 其他危险操作
        r'\b__builtins__\s*\[',
        r'\b__builtins__\s*\.',
        r'\b__import__\s*\(',
        r'\bimportlib\b',
        r'\bimp\b',
    ]
    
    # 检查代码中是否包含危险模式
    for pattern in dangerous_patterns:
        if re.search(pattern, code):
            return False, f"检测到危险代码模式: {pattern}"
    
    # 尝试解析AST，检查是否有危险的节点
    try:
        tree = ast.parse(code)
        
        # 危险模块列表（扩展）
        dangerous_modules = [
            'os', 'sys', 'subprocess', 'pymysql', 'sqlite3',
            'requests', 'urllib', 'http', 'socket', 'ftplib', 'telnetlib',
            'pickle', 'cpickle', 'marshal', 'ctypes',
            'multiprocessing', 'threading', 'concurrent',
            'importlib', 'imp', 'builtins'
        ]
        
        # 危险函数列表（扩展）
        # 注意：hasattr 是安全的，只用于检查属性，不用于访问
        dangerous_functions = [
            'eval', 'exec', 'compile', '__import__',
            'getattr', 'setattr', 'delattr',  # hasattr 已移除，它是安全的
            'globals', 'locals', 'vars', 'dir', 'type'
        ]
        
        # 检查是否有危险的函数调用
        for node in ast.walk(tree):
            # 检查是否有对危险函数的调用
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in dangerous_functions:
                        return False, f"检测到危险函数调用: {func_name}()"
                
                # 检查是否有os.system等调用
                if isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        if node.func.value.id in dangerous_modules:
                            return False, f"检测到危险模块调用: {node.func.value.id}.{node.func.attr}"
                    
                    # 检查是否有 getattr(builtins, '__import__') 等绕过方式
                    if isinstance(node.func, ast.Name) and node.func.id == 'getattr':
                        # 检查 getattr 的参数
                        if len(node.args) >= 2:
                            if isinstance(node.args[0], ast.Name) and node.args[0].id in ['builtins', '__builtins__']:
                                if isinstance(node.args[1], ast.Constant) and node.args[1].value in dangerous_functions:
                                    return False, f"检测到通过 getattr 绕过限制: getattr({node.args[0].id}, '{node.args[1].value}')"
        
        # 检查导入语句
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in dangerous_modules:
                        return False, f"检测到危险模块导入: {alias.name}"
            
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] in dangerous_modules:
                    return False, f"检测到危险模块导入: {node.module}"
        
        # 检查是否有访问 __builtins__ 的尝试
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                if isinstance(node.attr, str) and node.attr.startswith('__') and node.attr.endswith('__'):
                    if node.attr in ['__builtins__', '__import__', '__class__', '__bases__', '__subclasses__', '__mro__']:
                        # 检查是否在危险上下文中使用
                        if isinstance(node.value, ast.Name) and node.value.id in ['builtins', '__builtins__']:
                            return False, f"检测到访问危险属性: {node.value.id}.{node.attr}"
        
    except SyntaxError as e:
        return False, f"代码语法错误: {str(e)}"
    except Exception as e:
        # 如果AST解析失败，记录警告但允许继续（可能是代码不完整）
        logger.warning(f"AST parse failed; skipping safety checks: {str(e)}")
    
    return True, None
