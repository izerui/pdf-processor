from qiniu import Auth, put_file,put_data, build_batch_stat, BucketManager, build_batch_rename, build_batch_move, \
    build_batch_copy, build_batch_delete


class Bucket:
    """
    qiniu空间对象
    """
    __slots__ = ['profile', 'name', 'domain', 'is_public']

    def __init__(self, profile, name, domain, is_public):
        self.profile = profile
        self.name = name
        self.domain = domain
        self.is_public = is_public


buckets = [
    Bucket('prod', 'sz-yunji', 'file.yj2025.com', True),
    Bucket('prod', 'sz-yunji-private', 'pfile.yj2025.com', False),
    Bucket('dev', 'sz-yunji-dev', 'dfile.yj2025.com', True),
    Bucket('dev', 'sz-yunji-dev-private', 'pdfile.yj2025.com', False),
    Bucket('test', 'sz-yunji-test', 'tfile.yj2025.com', True),
    Bucket('test', 'sz-yunji-test-private', 'ptfile.yj2025.com', False)
]


class QiniuClient():

    def __init__(self):
        super().__init__()
        access_key = 'azamk57pyFWNZY3DZQYQnKZkRsC2k3FfD8hZFVEz'
        secret_key = '0vp7FYYy2kbbk0F9rWunv2tvqttQl1N7zO27TC5M'
        self.client = Auth(access_key, secret_key)

    def get_bucket(self, profile, is_public):
        """
        获取桶bucket, 在qiniu上的空间
        :param is_public: 是否公有
        :return:
        """
        filter_list = list(filter(lambda x: x.profile == profile and x.is_public == is_public, buckets))
        if filter_list:
            return filter_list[0]
        else:
            raise BaseException(f'未找到对应{profile}的{"公有" if is_public else "私有"}桶')

    def get_upload_token(self, profile, is_public, key):
        """
        获取用来上传文件的token
        :param profile: 选择环境 dev:开发环境、test:测试环境、prod:生产环境
        :param is_public: 是否公有空间
        :param key: 文件的key
        :return: token
        """
        bucket = self.get_bucket(profile, is_public)
        policy = {
            "returnBody": """{
                        "bucket": "$(bucket)",
                        "key": "$(key)",
                        "eTag": "$(etag)",
                        "fileSize":"$(fsize)",
                        "fileName": "$(fname)",
                        "filePrefix": "$(fprefix)",
                        "mimeType": "$(mimeType)",
                        "ext": "$(ext)"
                    }"""
        }
        token = self.client.upload_token(bucket.name, key, 3600, policy=policy)
        return token

    def upload_file(self, profile, is_public, key, local_file):
        """
        上传文件, 会自动获取token并验证上传
        :param profile: 选择环境 dev:开发环境、test:测试环境、prod:生产环境
        :param is_public: 是否公有空间
        :param key: 存在七牛上的文件的key
        :param local_file: 本地文件路径
        :return:
        """
        token = self.get_upload_token(profile, is_public, key)
        ret, info = put_file(token, key, local_file, version='v2')
        print(info)
        return ret

    def upload_data(self, profile, is_public, key, bytes):
        """
        上传文件, 会自动获取token并验证上传
        :param profile: 选择环境 dev:开发环境、test:测试环境、prod:生产环境
        :param is_public: 是否公有空间
        :param key: 存在七牛上的文件的key
        :param bytes: 二进制数组
        :return:
        """
        token = self.get_upload_token(profile, is_public, key)
        ret, info = put_data(token, key, bytes)
        print(info)
        return ret

    def get_file_stats(self, profile, is_public, keys: list):
        """
        获取qiniu存储文件的状态
        :param profile: 选择环境 dev:开发环境、test:测试环境、prod:生产环境
        :param is_public: 是否公有空间
        :param keys: 存在七牛上的文件的keys集合
        :return:
        """
        bucket_mgr = BucketManager(self.client)
        bucket = self.get_bucket(profile, is_public)
        ops = build_batch_stat(bucket.name, keys)
        ret, info = bucket_mgr.batch(ops)
        print(info)
        return ret

    def get_download_url(self, profile, is_public, key):
        """
        获取文件下载地址
        :param profile: 选择环境 dev:开发环境、test:测试环境、prod:生产环境
        :param is_public: 是否公有空间
        :param key: 存在七牛上的文件的key
        :return:
        """
        bucket = self.get_bucket(profile, is_public)
        base_url = 'https://%s/%s' % (bucket.domain, key)
        if not is_public:
            base_url = self.client.private_download_url(base_url, expires=3600)
        return base_url


    def list_files(self, profile, is_public, prefix = None, marker = None, limit = 10, delimiter = None):
        """
        获取指定前缀文件列表
        :param profile: 选择环境 dev:开发环境、test:测试环境、prod:生产环境
        :param is_public: 是否公有空间
        :param prefix: 前缀
        :param marker: 标记
        :param limit: 列举条目数
        :param delimiter: 分隔符， None: 列举出除'/'的所有文件以及以'/'为分隔的所有前缀
        :return:
        """
        bucket_mgr = BucketManager(self.client)
        bucket = self.get_bucket(profile, is_public)
        ret, eof, info = bucket_mgr.list(bucket.name, prefix, marker, limit, delimiter)
        print(info)
        return ret

    def batch_rename_files(self, profile, is_public, renames_obj, force: bool = False):
        """
        批量重命名文件
        :param profile: 选择环境 dev:开发环境、test:测试环境、prod:生产环境
        :param is_public: 是否公有空间
        :param renames_obj: 要改名的文件对象 {'src_key1': 'target_key1', 'src_key2': 'target_key2'}
        :param force: force为true时强制同名覆盖, 字典的键为原文件，值为目标文件
        :return:
        """
        bucket_mgr = BucketManager(self.client)
        bucket = self.get_bucket(profile, is_public)
        ops = build_batch_rename(bucket.name, renames_obj, force='true' if force else 'false')
        ret, info = bucket_mgr.batch(ops)
        print(info)
        return ret

    def batch_move_files(self, source_profile, source_is_public, target_profile, target_is_public, keys_obj, force: bool = False):
        """
        批量移动文件
        :param source_profile: 源文件的环境
        :param source_is_public: 源文件的公有空间或者私有空间
        :param target_profile: 目的文件的环境
        :param target_is_public: 目的文件的公有空间或者私有空间
        :param keys_obj: 要移动的： {'src_key1': 'target_key1', 'src_key2': 'target_key2'}
        :param force: force为true时强制同名覆盖, 字典的键为原文件，值为目标文件
        :return:
        """
        bucket_mgr = BucketManager(self.client)
        source_bucket = self.get_bucket(source_profile, source_is_public)
        target_bucket = self.get_bucket(target_profile, target_is_public)
        # force为true时强制同名覆盖, 字典的键为原文件，值为目标文件
        ops = build_batch_move(source_bucket.name, keys_obj,
                               target_bucket.name, force='true' if force else 'false')
        ret, info = bucket_mgr.batch(ops)
        print(info)
        return ret

    def batch_copy_files(self, source_profile, source_is_public, target_profile, target_is_public, keys_obj, force: bool = False):
        """
        批量复制文件
        :param source_profile: 源文件的环境
        :param source_is_public: 源文件的公有空间或者私有空间
        :param target_profile: 目的文件的环境
        :param target_is_public: 目的文件的公有空间或者私有空间
        :param keys_obj: 要复制的： {'src_key1': 'target_key1', 'src_key2': 'target_key2'}
        :param force: force为true时强制同名覆盖, 字典的键为原文件，值为目标文件
        :return:
        """
        bucket_mgr = BucketManager(self.client)
        source_bucket = self.get_bucket(source_profile, source_is_public)
        target_bucket = self.get_bucket(target_profile, target_is_public)
        # force为true时强制同名覆盖, 字典的键为原文件，值为目标文件
        ops = build_batch_copy(source_bucket.name, keys_obj,
                               target_bucket.name, force='true' if force else 'false')
        ret, info = bucket_mgr.batch(ops)
        print(info)
        return ret

    def batch_delete_files(self, profile, is_public, keys: list):
        """
        批量删除文件
        :param profile: 选择环境 dev:开发环境、test:测试环境、prod:生产环境
        :param is_public: 是否公有空间
        :param keys: 文件列表 ['1.gif', '2.txt', '3.png', '4.html']
        :return:
        """
        bucket_mgr = BucketManager(self.client)
        bucket = self.get_bucket(profile, is_public)
        # force为true时强制同名覆盖, 字典的键为原文件，值为目标文件
        ops = build_batch_delete(bucket.name, keys)
        ret, info = bucket_mgr.batch(ops)
        print(info)
        return ret