from tornado import gen
from traitlets.config import LoggingConfigurable, Config
from docker.types import DriverConfig


class Mounter(LoggingConfigurable):

    def __init__(self, config):
        LoggingConfigurable.__init__(self)
        if not isinstance(config, dict):
            raise Exception("A dictionary typed config is expected")
        if not config:
            raise Exception("A non-zero sized dictionary is expected")
        self.config = Config(config)

    @gen.coroutine
    def create(self, data=None):
        return None


class LocalVolumeMounter(Mounter):

    def __init__(self, config):
        super(Mounter).__init__(config)

    @gen.coroutine
    def create(self, data=None):
        return None


class SSHFSMounter(Mounter):

    def __init__(self, config):
        Mounter.__init__(self, config)

    @gen.coroutine
    def create_mount(self, data):
        self.log.debug("create_mount: {}".format(data))

        # validate required driver data is present
        err, err_msg = False, []
        if 'sshcmd' not in self.config['driver_options'] \
                or self.config['driver_options']['sshcmd'] == '':
            err_msg.append("create_mount requires that the 'sshcmd'"
                           "driver_options key is set to a nonempty value")
            err = True

        if 'id_rsa' not in self.config['driver_options'] \
                and 'password' not in self.config['driver_options'] \
                or 'id_rsa' in self.config['driver_options'] \
                and 'password' in self.config['driver_options']:
            err_msg.append("create_mount requires either a 'id_rsa' or 'password' "
                           "driver_options key")
            err = True

        if 'id_rsa' in self.config['driver_options'] \
                and self.config['driver_options']['id_rsa'] == '' \
                or 'password' in self.config['driver_options'] \
                and self.config['driver_options']['password'] == '':
            err_msg.append("create_mount requires a nonempty value from either "
                           "'id_rsa' or 'password'")
            err = True

        if err:
            self.log.error("create_mount failed: {}".format(','.join(err_msg)))
            raise Exception("An error occurred during mount creation")

        mount = {'driver_config': self.config['driver_config'],
                 'driver_options': {}.update(self.config['driver_options'])}

        # Dynamic mount target
        if self.config['driver_options']['sshcmd'] == '{sshcmd}':
            # Validate that the proper values are present
            username = yield self.get_from_data('USERNAME')
            path = yield self.get_from_data('PATH')
            mount['driver_options']['sshcmd'] = username + path

        if self.config['driver_options']['id_rsa'] == '{id_rsa}':
            key = yield self.get_from_data('PRIVATEKEY')
            mount['driver_options']['id_rsa'] = key

        return DriverConfig(name=mount['driver_config'], options=mount['driver_options'])

    @gen.coroutine
    def validate_config(self):
        self.log.debug("validate_config")
        required_config_keys = ['type', 'driver_config',
                                'driver_options', 'source', 'target']
        missing_keys = [key for key in required_config_keys if key not in self.config]

        if missing_keys:
            self.log.error("Missing configure keys {}".format(','.join(missing_keys)))
            raise Exception("A mount configuration error was encountered, "
                            "due to missing keys")

        empty_values = [key for key in required_config_keys if not self.config[key]]
        if empty_values:
            self.log.error("Missing configuring values {}".format(','.join(empty_values)))
            raise Exception("A mount configuration error was encountered, "
                            "due to missing values")

        # validate types
        for key, val in self.config.items():
            if key == 'driver_options':
                if not isinstance(val, dict):
                    raise Exception("{} is expected to be of a {} type".format(key, dict))
            else:
                if not isinstance(val, str):
                    raise Exception("{} is expected to be of {} type".format(key, str))

    @gen.coroutine
    def get_from_data(self, data):
        pass


    # @gen.coroutine
    # def validate_data(self, data):
    #     self.log.debug("validate_data: {}".format(data))
    #     if data is None:
    #         self.log.error("validate_data {} has not been set".format(data))
    #         raise Exception("Missing information to mount the host in question with."
    #                         "Try to reinitialize them")
    #
    #     if not isinstance(data, dict):
    #         self.log.error("validate_data {} is expected to be of a {} type".format(
    #             data, dict))
    #         raise Exception("The data required for mounting a specific host is "
    #                         "incorrectly formatted")
    #
    #     # Validate required dictionary keys
    #     required_keys = ['HOST', 'USERNAME', 'PATH', 'PRIVATEKEY']
    #     missing_keys = [key for key in required_keys
    #                     for d_key, d_val in data.items()
    #                     if key not in data and key not in d_val]
    #
    #     # Skip validation if debug
    #     if missing_keys:
    #         self.log.error("Missing mount keys: {}".format(",".join(missing_keys)))
    #         raise Exception("The data required for mounting a specific host is not "
    #                         "present, Try to reinitialize them")
    #
    #     empty_values = [val for key, val in data.items() if not data[key]]
    #     if empty_values:
    #         self.log.error("Missing mount data values {}".format(','.join(empty_values)))
    #         raise Exception("A mount configuration error was encountered, "
    #                         "due to empty data values")

    @gen.coroutine
    def create(self, data=None):
        self.log.info("Creating a new mount {}".format(data))
        yield self.validate_config()
        mount = yield self.create_mount(data)
        return mount
