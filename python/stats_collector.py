#!/usr/bin/env python2
#
# DO NOT ALTER OR REMOVE COPYRIGHT NOTICES OR THIS FILE HEADER
#
# Copyright (c) 2018, Juniper Networks, Inc. All rights reserved.
#
#
# The contents of this file are subject to the terms of the BSD 3 clause
# License (the "License"). You may not use this file except in compliance
# with the License.
#
# You can obtain a copy of the license at
# https://github.com/Juniper/warp17/blob/master/LICENSE.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from this
# software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
#
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# File name:
#    stats_collector.py
#
# Description:
#    Memory stats aggregator.
#
# Author:
#    Matteo Triggiani
#
# Initial Created:
#    10/03/2018
#
# Notes:
#


# ****************************************************************************
# Include files
# ****************************************************************************
from warp17_api import *
import time

from rpc_impl import *
from functools import partial
from time import sleep
from datetime import datetime
from b2b_setup import *

from uniq import get_uniq_stamp
from warp17_common_pb2 import *
from warp17_l3_pb2 import *
from warp17_app_raw_pb2 import *
from warp17_app_pb2 import *
from warp17_server_pb2 import *
from warp17_app_http_pb2 import *
from warp17_client_pb2 import *
from warp17_test_case_pb2 import *
from warp17_service_pb2 import *
from warp17_sockopt_pb2 import *
import errno
import pdb

local_dir = os.getcwd()

env = Warp17Env('ut/ini/{}.ini'.format(socket.gethostname()))
warp17_call = partial(warp17_method_call, env.get_host_name(),
                      env.get_rpc_port(), Warp17_Stub)
bin = "{}/build/warp17".format(local_dir)


# TODO: instead of having a test class with server/client testcases preset
#  we should have a testcase class with one generic testcase and eventually a
#  secondary class with two default testcases server/client
class Test():

    def __init__(self, type=None, port=None, id=None):
        # l3_config = {
        #     port : [
        #         def_gw,
        #         n_ip]
        # }
        self.l3_config = {
            0: [0,
                1],
            1: [0,
                1]
        }
        # self.l4_config = {
        #     port: n_ports
        # }
        self.l4_config = {
            0: 1,
            1: 1,
        }
        self.tcpwin = None
        self.mtu = 1500
        if type is TestCaseType.Value('CLIENT'):
            self.rate_ccfg = RateClient(rc_open_rate=Rate(),
                                        rc_close_rate=Rate(),
                                        rc_send_rate=Rate())
            self.app_ccfg = App()

            self.l4_ccfg = L4Client()

            self.init_delay = Delay(d_value=0)
            self.uptime = Delay()
            self.downtime = Delay(d_value=0)

            self.ccfg = TestCase()
            self.cl_port = port
            self.tc_id = id
            self.test_type = type
        elif type is TestCaseType.Value('SERVER'):
            self.sr_test_criteria = TestCriteria(tc_crit_type=SRV_UP,
                                                 tc_srv_up=1)

            self.l4_scfg = L4Server()
            self.scfg = TestCase()
            self.sr_port = port
            self.tc_id = id
            self.test_type = type
        elif type is None and port is None:
            self.rate_ccfg = RateClient(rc_open_rate=Rate(),
                                        rc_close_rate=Rate(),
                                        rc_send_rate=Rate())
            self.app_ccfg = App()

            self.l4_ccfg = L4Client()

            self.init_delay = Delay(d_value=0)
            self.uptime = Delay()
            self.downtime = Delay(d_value=0)

            self.ccfg = TestCase()
            self.sr_test_criteria = TestCriteria(tc_crit_type=SRV_UP,
                                                 tc_srv_up=1)

            self.l4_scfg = L4Server()
            self.scfg = TestCase()
            self.cl_port = 0
            self.sr_port = 1
            self.tc_id = 0 if id is None else id
            self.test_type = None
        else:
            raise BaseException("ERROR: Wrong test type.")

    def add_l3(self, port, def_gw, n_ip):
        self.l3_config[port] = [def_gw, n_ip]

    def add_config(self):
        # TODO: enable multiple server/client tests
        if self.test_type is TestCaseType.Value('CLIENT'):

            def_gw, n_ip = self.l3_config[self.cl_port]
            pcfg = b2b_port_add(self.cl_port,
                                def_gw=Ip(ip_version=IPV4, ip_v4=def_gw))
            b2b_port_add_intfs(pcfg,
                               [(Ip(ip_version=IPV4,
                                    ip_v4=b2b_ipv4(self.cl_port, i)),
                                 Ip(ip_version=IPV4,
                                    ip_v4=b2b_mask(self.cl_port, i)),
                                 b2b_count(self.cl_port, i)) for i in
                                range(0, 1)])
            warp17_call('ConfigurePort', pcfg)

            self.l4_ccfg = L4Client(l4c_proto=self.proto,
                                    l4c_tcp_udp=TcpUdpClient(
                                        tuc_sports=b2b_ports(
                                            self.l4_config[self.cl_port]),
                                        tuc_dports=b2b_ports(
                                            self.l4_config[self.sr_port])))
            cl_src_ips = b2b_sips(self.cl_port, self.l3_config[self.cl_port][1])
            cl_dst_ips = b2b_sips(self.sr_port, self.l3_config[self.sr_port][1])
            self.ccfg = TestCase(tc_type=CLIENT, tc_eth_port=self.cl_port,
                                 tc_id=self.tc_id,
                                 tc_client=Client(cl_src_ips=cl_src_ips,
                                                  cl_dst_ips=cl_dst_ips,
                                                  cl_l4=self.l4_ccfg,
                                                  cl_rates=self.rate_ccfg),
                                 tc_app=self.app_ccfg,
                                 tc_init_delay=self.init_delay,
                                 tc_uptime=self.uptime,
                                 tc_downtime=self.downtime,
                                 tc_criteria=self.cl_test_criteria,
                                 tc_async=True)
            self.configure_tc(self.ccfg, self.cl_port)
        elif self.test_type is TestCaseType.Value('SERVER'):

            def_gw, n_ip = self.l3_config[self.sr_port]
            pcfg = b2b_port_add(self.sr_port,
                                def_gw=Ip(ip_version=IPV4, ip_v4=def_gw))
            b2b_port_add_intfs(pcfg,
                               [(Ip(ip_version=IPV4,
                                    ip_v4=b2b_ipv4(self.sr_port, i)),
                                 Ip(ip_version=IPV4,
                                    ip_v4=b2b_mask(self.sr_port, i)),
                                 b2b_count(self.sr_port, i)) for i in
                                range(0, 1)])
            warp17_call('ConfigurePort', pcfg)
            self.l4_scfg = L4Server(l4s_proto=self.proto,
                                    l4s_tcp_udp=TcpUdpServer(
                                        tus_ports=b2b_ports(1)))
            srv_src_ips = b2b_sips(self.sr_port,
                                   self.l3_config[self.sr_port][1])
            self.scfg = TestCase(tc_type=SERVER, tc_eth_port=self.sr_port,
                                 tc_id=self.tc_id,
                                 tc_server=Server(srv_ips=srv_src_ips,
                                                  srv_l4=self.l4_scfg),
                                 tc_app=self.app_scfg,
                                 tc_criteria=self.sr_test_criteria,
                                 tc_async=True)
            self.configure_tc(self.scfg, self.sr_port)
        elif self.test_type is None:

            for port in self.l3_config:
                def_gw, n_ip = self.l3_config[port]
                pcfg = b2b_port_add(port,
                                    def_gw=Ip(ip_version=IPV4, ip_v4=def_gw))
                b2b_port_add_intfs(pcfg,
                                   [(Ip(ip_version=IPV4,
                                        ip_v4=b2b_ipv4(port, i)),
                                     Ip(ip_version=IPV4,
                                        ip_v4=b2b_mask(port, i)),
                                     b2b_count(port, i)) for i in range(0, 1)])
                warp17_call('ConfigurePort', pcfg)

                if self.mtu is not 1500:  # 1500 is the default MTU
                    port_options = PortOptions(po_mtu=self.mtu)
                    answer = warp17_call('SetPortOptions',
                                         PortOptionsArg(
                                             poa_port=PortArg(pa_eth_port=port),
                                             poa_opts=port_options))
                    if answer.e_code is not 0:
                        raise BaseException("ERROR {} configuring port {}"
                                            "".format(answer.e_code, port))

            self.l4_ccfg = L4Client(l4c_proto=self.proto,
                                    l4c_tcp_udp=TcpUdpClient(
                                        tuc_sports=b2b_ports(
                                            self.l4_config[self.cl_port]),
                                        tuc_dports=b2b_ports(
                                            self.l4_config[self.sr_port])))
            cl_src_ips = b2b_sips(self.cl_port, self.l3_config[self.cl_port][1])
            cl_dst_ips = b2b_sips(self.sr_port, self.l3_config[self.sr_port][1])
            self.ccfg = TestCase(tc_type=CLIENT, tc_eth_port=self.cl_port,
                                 tc_id=self.tc_id,
                                 tc_client=Client(cl_src_ips=cl_src_ips,
                                                  cl_dst_ips=cl_dst_ips,
                                                  cl_l4=self.l4_ccfg,
                                                  cl_rates=self.rate_ccfg),
                                 tc_app=self.app_ccfg,
                                 tc_init_delay=self.init_delay,
                                 tc_uptime=self.uptime,
                                 tc_downtime=self.downtime,
                                 tc_criteria=self.cl_test_criteria,
                                 tc_async=True)
            self.configure_tc(self.ccfg, self.cl_port)

            if self.tcpwin is not None:
                time.sleep(1)
                sockopt_arg = TcpSockoptArg(
                    toa_tc_arg=TestCaseArg(tca_eth_port=self.cl_port,
                                           tca_test_case_id=self.tc_id),
                    toa_opts=TcpSockopt(
                        to_win_size=self.tcpwin))
                answer = warp17_call('SetTcpSockopt', sockopt_arg)

                if answer.e_code is not 0:
                    raise BaseException(
                        'ERROR {} configuring tcp option {}'.format(
                            answer.e_code, sockopt_arg))

            self.l4_scfg = L4Server(l4s_proto=self.proto,
                                    l4s_tcp_udp=TcpUdpServer(
                                        tus_ports=b2b_ports(
                                            self.l4_config[self.sr_port])))
            srv_src_ips = b2b_sips(self.sr_port,
                                   self.l3_config[self.sr_port][1])
            assert (cl_dst_ips == srv_src_ips)
            self.scfg = TestCase(tc_type=SERVER, tc_eth_port=self.sr_port,
                                 tc_id=self.tc_id,
                                 tc_server=Server(srv_ips=srv_src_ips,
                                                  srv_l4=self.l4_scfg),
                                 tc_app=self.app_scfg,
                                 tc_criteria=self.sr_test_criteria)
            self.configure_tc(self.scfg, self.sr_port)

            if self.tcpwin is not None:
                time.sleep(1)
                sockopt_arg = TcpSockoptArg(
                    toa_tc_arg=TestCaseArg(tca_eth_port=self.sr_port,
                                           tca_test_case_id=self.tc_id),
                    toa_opts=TcpSockopt(
                        to_win_size=self.tcpwin))
                answer = warp17_call('SetTcpSockopt', sockopt_arg)

                if answer.e_code is not 0:
                    raise BaseException(
                        'ERROR {} configuring tcp option {}'.format(
                            answer.e_code, sockopt_arg))
        else:
            raise BaseException("ERROR: test type is invalid")

    # Dirty hack to make sure there aren't testcases already configured
    @staticmethod
    def configure_tc(cfg, port):
        answer = warp17_call('ConfigureTestCase', cfg)
        if answer.e_code == -long(errno.EALREADY) or answer.e_code == \
                -long(errno.EEXIST):
            # print("ERROR {}: trying to reconfigure".format(answer.e_code))
            # TODO: clean all the possible testcases
            warp17_call('PortStop', PortArg(pa_eth_port=port))
            warp17_call('DelTestCase', cfg)
            answer = warp17_call('ConfigureTestCase', cfg)
        if answer.e_code is not 0:
            pdb.set_trace()
            raise BaseException("ERROR {} configuring testcase"
                                "".format(answer.e_code))

    def collect_results(self, times=1):
        status = []
        stats = []
        tstamps = []
        sleep(10)  # wait for test to be fully running before start colleting
        # stats
        while times >= 0:
            status1 = {}
            stats1 = {}
            for port in self.l3_config:
                status1[port] = warp17_call('GetTestStatus',
                                            TestCaseArg(tca_eth_port=port,
                                                        tca_test_case_id=self.tc_id))
                stats1[port] = warp17_call('GetStatistics',
                                           TestCaseArg(tca_eth_port=port,
                                                       tca_test_case_id=self.tc_id))
                tstamp1 = time.time()
            status.append(status1)
            stats.append(stats1)
            tstamps.append(tstamp1)
            time.sleep(1)
            times -= 1

        return status, stats, tstamps

    def stop(self):
        for port in self.l3_config:
            answer = warp17_call('PortStop', PortArg(pa_eth_port=port))
            if answer.e_code is not 0:
                print("ERROR {} stopping testcases on port {}".format(answer.e_code, port))

    # DEBUG function that tries to get the testcase and prints it
    #   ATTENTION: use it only after you configured the testcases
    def check_test(self):
        for port in self.l3_config:
            answer = warp17_call('GetTestCase', TestCaseArg(
                tca_eth_port=port, tca_test_case_id=0))
            if answer.tcr_error.e_code is not 0:
                raise BaseException(
                    "ERROR {} GetTestCase testcases on port {}"
                    "".format(answer.tcr_error.e_code, port))
            print(answer.tcr_cfg)

    def start(self, port=None):
        if port is not None and type(port) is int:
            answer = warp17_call('PortStart', PortArg(pa_eth_port=port))
            if answer.e_code is not 0:
                raise BaseException("ERROR {} stopping testcases on port {}"
                                    "".format(answer.e_code, port))
        else:
            for port in self.l3_config:
                answer = warp17_call('PortStart', PortArg(pa_eth_port=port))
                if answer.e_code is not 0:
                    raise BaseException("ERROR {} starting testcases on port {}"
                                        "".format(answer.e_code, port))

    @staticmethod
    def passed(results):
        """Check if the tests has passed"""
        client_result = results[0]
        server_result = results[1]
        if (server_result.tsr_state != PASSED or
                client_result.tsr_state != PASSED):
            return False
        return True


# TODO: adapt this to the new test class
def search_mimimum_memory(pivot, R):
    """Binary search the minimum memory needed to run the test"""
    localenv = Warp17Env('ut/ini/{}.ini'.format(socket.gethostname()))
    if R < precision:
        return
    print("Running warp17 on {}Mb memory".format(pivot))
    not_started = False
    localenv.set_value(env.MEMORY, pivot)

    try:
        oarg = Warp17OutputArgs(out_file=log_file)
        proc = warp17_start(env=localenv, exec_file=bin, output_args=oarg)

    except BaseException as E:
        print("Error occurred: {}".format(E))
        exit(-1)

    try:
        warp17_wait(env)

        status, stats, tstamps = test.run()

    except BaseException as E:
        print("Error occurred: {}".format(E))
        not_started = True
        pass

    if warp17_stop(env, proc) != 0:
        os.kill(proc)
    time.sleep(1)

    if not not_started:
        if test.passed(status):
            message = "Success run with {}Mb memory\n".format(pivot)
            resultwriter.write(message)
            search_mimimum_memory(pivot - R / 2, R / 2)
            return
    message = "Failed run with {}Mb memory\n".format(pivot)
    resultwriter.write(message)
    search_mimimum_memory(pivot + R / 2, R / 2)
    return


def collect_stats(logwriter, localenv, test_list):
    print("Running warp17 on {}".format(localenv))

    try:
        oarg = Warp17OutputArgs(out_file=log_file)
        proc = warp17_start(env=localenv, exec_file=bin, output_args=oarg)

    except BaseException as E:
        print("Error occurred: {}".format(E))
        exit(-1)

    try:
        warp17_wait(localenv)

    except BaseException as E:
        print("ERROR {} starting warp17".format(E))
        warp17_stop(localenv, proc)

        n_samples = 20
        sample = 0
        status = []
        stats = []
        tstamps = []
        for test in test_list:
            test.add_config()
            # test.check_test()  # use to debug only
            test.start()

        sleep(15)   # wait for test to be fully running
                    #  (http tests take a lot of time)
        init_tstamp = time.time()
        while sample <= n_samples:
            status1 = {}
            stats1 = {}
            for port in (0, 1):
                status1[port] = warp17_call('GetTestStatus',
                                            TestCaseArg(tca_eth_port=port,
                                                        tca_test_case_id=0))
                stats1[port] = warp17_call('GetStatistics',
                                           TestCaseArg(tca_eth_port=port,
                                                       tca_test_case_id=0))
            tstamp_diff = time.time() - init_tstamp
            status.append(status1)
            stats.append(stats1)
            tstamps.append(tstamp_diff)
            time.sleep(0.5)
            sample += 1

        for test in test_list:
            test.stop()

        warp17_stop(localenv, proc)
        i = 0

        while i < len(stats):
            stats1 = stats[i]
            status1 = status[i]
            tstamps1 = tstamps[i]
            message = "timestamp={:.2f},".format(tstamps1)
            for port in (0, 1):
                phystats = stats1[port].sr_phy_rate
                statusstats = status1[port].tsr_stats
                link_speed_bytes = float(phystats.pys_link_speed) * 1000 * 1000 / 8

                tx_usage = min(float(phystats.pys_tx_bytes) * 100 / link_speed_bytes, 100.0)
                rx_usage = min(float(phystats.pys_rx_bytes) * 100 / link_speed_bytes, 100.0)
                message += "port={},".format(port)
                message += "rx_usage={:.2f},".format(rx_usage)
                message += "tx_usage={:.2f},".format(tx_usage)
                message += "gs_estab={},".format(statusstats.gs_estab)
            message += "\n"
            logwriter.write(message)
            i += 1


    return


def wait_collect_stats(logwriter, localenv, test_list):
    print("Running warp17 on {}".format(localenv))

    try:
        warp17_wait(localenv)

    except BaseException as E:
        print("ERROR {} starting warp17".format(E))

    n_samples = 20
    sample = 0
    status = []
    stats = []
    tstamps = []
    for test in test_list:
        test.add_config()
        # test.check_test()  # use to debug only
        # ATTENTION dirty hack to make this class working with a single test
        #  configured, TODO it has to be cleaned
        test.start(0)

    sleep(60)  # wait for test to be fully running
    #     (http tests take a lot of time)
    init_tstamp = time.time()
    while sample <= n_samples:
        status1 = {}
        stats1 = {}
        for port in (0, 1):
            status1[port] = warp17_call('GetTestStatus',
                                        TestCaseArg(tca_eth_port=port,
                                                    tca_test_case_id=0))
            stats1[port] = warp17_call('GetStatistics',
                                       TestCaseArg(tca_eth_port=port,
                                                   tca_test_case_id=0))
        tstamp_diff = time.time() - init_tstamp
        status.append(status1)
        stats.append(stats1)
        tstamps.append(tstamp_diff)
        time.sleep(0.5)
        sample += 1

    for test in test_list:
        test.stop()

    warp17_stop(localenv, proc)
    i = 0

    while i < len(stats):
        stats1 = stats[i]
        status1 = status[i]
        tstamps1 = tstamps[i]
        message = "timestamp={:.2f},".format(tstamps1)
        for port in (0, 1):
            phystats = stats1[port].sr_phy_rate
            statusstats = status1[port].tsr_stats
            link_speed_bytes = float(
                phystats.pys_link_speed) * 1000 * 1000 / 8

            tx_usage = min(
                float(phystats.pys_tx_bytes) * 100 / link_speed_bytes,
                100.0)
            rx_usage = min(
                float(phystats.pys_rx_bytes) * 100 / link_speed_bytes,
                100.0)
            message += "port={},".format(port)
            message += "rx_usage={:.2f},".format(rx_usage)
            message += "tx_usage={:.2f},".format(tx_usage)
            message += "gs_estab={},".format(statusstats.gs_estab)
        message += "\n"
        logwriter.write(message)
        i += 1

def test_http_throughput():
    """Configures a test to run 10 million sessions"""
    localenv = Warp17Env('ut/ini/{}.ini'.format(socket.gethostname()))
    test_10m = Test()
    test_10m.cl_port = 0
    test_10m.sr_port = 1
    test_10m.add_l3(test_10m.cl_port, 167837697, 2)
    test_10m.add_l3(test_10m.sr_port, 167772161, 1)
    test_10m.l4_config[test_10m.cl_port] = 200
    test_10m.l4_config[test_10m.sr_port] = 50000
    test_10m.proto = TCP

    test_10m.cl_test_criteria = TestCriteria(tc_crit_type=RUN_TIME,
                                             tc_cl_estab=120)

    test_10m.app_ccfg = App(app_proto=HTTP_CLIENT,
                            app_http_client=HttpClient(hc_req_method=GET,
                                                       hc_req_object_name='/index.html',
                                                       hc_req_host_name='www.foobar.net',
                                                       hc_req_size=512))
    test_10m.app_scfg = App(app_proto=HTTP_SERVER,
                            app_http_server=HttpServer(hs_resp_code=OK_200,
                                                       hs_resp_size=512))

    start_memory = env.get_memory()

    localenv.set_value(env.TCB_POOL_SZ, 95000)
    localenv.set_value(env.UCB_POOL_SZ, 0)

    out_folder = "/tmp/{}-test-{}/".format(test_http_throughput.__name__,
                                           get_uniq_stamp())

    return [test_10m], start_memory, out_folder, localenv


def test_udp_throughput():
    localenv = Warp17Env('ut/ini/{}.ini'.format(socket.gethostname()))
    test_thr = Test(id=0)
    test_thr.cl_port = 0
    test_thr.sr_port = 1
    test_thr.add_l3(test_thr.cl_port, 167837697, 1)  # 10.1.0.1
    test_thr.add_l3(test_thr.sr_port, 167772161, 10)  # 10.0.0.1-10.0.0.10
    test_thr.l4_config[test_thr.cl_port] = 10
    test_thr.l4_config[test_thr.sr_port] = 50000  # not really needed
    test_thr.proto = UDP

    test_thr.cl_test_criteria = TestCriteria(tc_crit_type=RUN_TIME,
                                             tc_cl_estab=120)

    test_thr.app_ccfg = App(app_proto=RAW_CLIENT,
                            app_raw_client=RawClient(rc_req_plen=1324,
                                                     rc_resp_plen=1324))
    test_thr.app_scfg = App(app_proto=RAW_SERVER,
                            app_raw_server=RawServer(rs_req_plen=1324,
                                                     rs_resp_plen=1324))

    test_thr.tc_init_delay = Delay(d_value=0)
    test_thr.tc_uptime = Delay(d_value=1)
    test_thr.tc_downtime = Delay(d_value=0)

    test_thr2 = Test(id=1)
    test_thr2.cl_port = 1
    test_thr2.sr_port = 0
    test_thr2.add_l3(test_thr2.cl_port, 167837697, 1)  # 10.1.0.1
    test_thr2.add_l3(test_thr2.sr_port, 167772161, 10)  # 10.0.0.1-10.0.0.10
    test_thr2.l4_config[test_thr2.cl_port] = 10
    test_thr2.l4_config[test_thr2.sr_port] = 50000  # not really needed
    test_thr2.proto = UDP

    test_thr2.cl_test_criteria = TestCriteria(tc_crit_type=RUN_TIME,
                                              tc_cl_estab=120)

    test_thr2.app_ccfg = App(app_proto=RAW_CLIENT,
                             app_raw_client=RawClient(rc_req_plen=1324,
                                                      rc_resp_plen=1324))
    test_thr2.app_scfg = App(app_proto=RAW_SERVER,
                             app_raw_server=RawServer(rs_req_plen=1324,
                                                      rs_resp_plen=1324))

    test_thr2.tc_init_delay = Delay(d_value=0)
    test_thr2.tc_uptime = Delay(d_value=1)
    test_thr2.tc_downtime = Delay(d_value=0)

    start_memory = env.get_memory()

    localenv.set_value(env.TCB_POOL_SZ, 0)
    localenv.set_value(env.UCB_POOL_SZ, 98000)

    out_folder = "/tmp/{}-test-{}/".format(test_udp_throughput.__name__,
                                           get_uniq_stamp())

    return [test_thr, test_thr2], start_memory, out_folder, localenv


def test_tcp_throughput():
    localenv = Warp17Env('ut/ini/{}.ini'.format(socket.gethostname()))
    test_thr = Test()
    test_thr.cl_port = 0
    test_thr.sr_port = 1
    test_thr.add_l3(test_thr.cl_port, 167837697, 4)  # 10.1.0.1
    test_thr.add_l3(test_thr.sr_port, 167772161, 1)  # 10.0.0.1-10.0.0.10
    test_thr.l4_config[test_thr.cl_port] = 200
    test_thr.l4_config[test_thr.sr_port] = 50000  # not really needed
    test_thr.proto = TCP

    test_thr.cl_test_criteria = TestCriteria(tc_crit_type=RUN_TIME,
                                             tc_cl_estab=120)

    test_thr.app_ccfg = App(app_proto=RAW_CLIENT,
                            app_raw_client=RawClient(rc_req_plen=512,
                                                     rc_resp_plen=512))
    test_thr.app_scfg = App(app_proto=RAW_SERVER,
                            app_raw_server=RawServer(rs_req_plen=512,
                                                     rs_resp_plen=512))

    test_thr.tc_init_delay = Delay(d_value=0)
    test_thr.tc_uptime = Delay(d_value=1)
    test_thr.tc_downtime = Delay(d_value=0)

    start_memory = env.get_memory()

    localenv.set_value(env.TCB_POOL_SZ, 98000)
    localenv.set_value(env.UCB_POOL_SZ, 0)

    out_folder = "/tmp/{}-test-{}/".format(test_tcp_throughput.__name__,
                                           get_uniq_stamp())

    return [test_thr], start_memory, out_folder, localenv


def test_tcp2_throughput():
    localenv = Warp17Env('ut/ini/{}.ini'.format(socket.gethostname()))
    test_thr = Test()
    test_thr.cl_port = 0
    test_thr.sr_port = 1
    test_thr.add_l3(test_thr.cl_port, 167837697, 4)  # 10.1.0.1
    test_thr.add_l3(test_thr.sr_port, 167772161, 1)  # 10.0.0.1-10.0.0.10
    test_thr.l4_config[test_thr.cl_port] = 200
    test_thr.l4_config[test_thr.sr_port] = 50000  # not really needed
    test_thr.proto = TCP

    test_thr.cl_test_criteria = TestCriteria(tc_crit_type=RUN_TIME,
                                             tc_cl_estab=120)

    test_thr.app_ccfg = App(app_proto=RAW_CLIENT,
                            app_raw_client=RawClient(rc_req_plen=1024,
                                                     rc_resp_plen=1024))
    test_thr.app_scfg = App(app_proto=RAW_SERVER,
                            app_raw_server=RawServer(rs_req_plen=1024,
                                                     rs_resp_plen=1024))

    test_thr.tc_init_delay = Delay(d_value=0)
    test_thr.tc_uptime = Delay(d_value=1)
    test_thr.tc_downtime = Delay(d_value=0)

    start_memory = env.get_memory()

    localenv.set_value(env.TCB_POOL_SZ, 98000)
    localenv.set_value(env.UCB_POOL_SZ, 0)

    out_folder = "/tmp/{}-test-{}/".format(test_tcp2_throughput.__name__,
                                           get_uniq_stamp())

    return [test_thr], start_memory, out_folder, localenv


def test_tcp3_throughput():
    localenv = Warp17Env('ut/ini/{}.ini'.format(socket.gethostname()))
    test_thr = Test()
    test_thr.cl_port = 0
    test_thr.sr_port = 1
    test_thr.add_l3(test_thr.cl_port, 167837697, 4)  # 10.1.0.1
    test_thr.add_l3(test_thr.sr_port, 167772161, 1)  # 10.0.0.1-10.0.0.10
    test_thr.l4_config[test_thr.cl_port] = 200
    test_thr.l4_config[test_thr.sr_port] = 50000  # not really needed
    test_thr.proto = TCP
    test_thr.mtu = 2854
    test_thr.tcpwin = 2560

    test_thr.cl_test_criteria = TestCriteria(tc_crit_type=RUN_TIME,
                                             tc_cl_estab=120)

    test_thr.app_ccfg = App(app_proto=RAW_CLIENT,
                            app_raw_client=RawClient(rc_req_plen=2560,
                                                     rc_resp_plen=2560))
    test_thr.app_scfg = App(app_proto=RAW_SERVER,
                            app_raw_server=RawServer(rs_req_plen=2560,
                                                     rs_resp_plen=2560))

    test_thr.tc_init_delay = Delay(d_value=0)
    test_thr.tc_uptime = Delay(d_value=1)
    test_thr.tc_downtime = Delay(d_value=0)

    start_memory = env.get_memory()

    localenv.set_value(env.TCB_POOL_SZ, 98000)
    localenv.set_value(env.UCB_POOL_SZ, 0)

    out_folder = "/tmp/{}-test-{}/".format(test_tcp3_throughput.__name__,
                                           get_uniq_stamp())

    return [test_thr], start_memory, out_folder, localenv


def test_tcp4_throughput():
    localenv = Warp17Env('ut/ini/{}.ini'.format(socket.gethostname()))
    test_thr = Test()
    test_thr.cl_port = 0
    test_thr.sr_port = 1
    test_thr.add_l3(test_thr.cl_port, 167837697, 4)  # 10.1.0.1
    test_thr.add_l3(test_thr.sr_port, 167772161, 1)  # 10.0.0.1-10.0.0.10
    test_thr.l4_config[test_thr.cl_port] = 200
    test_thr.l4_config[test_thr.sr_port] = 50000  # not really needed
    test_thr.proto = TCP
    test_thr.mtu = 5414
    test_thr.tcpwin = 5120

    test_thr.cl_test_criteria = TestCriteria(tc_crit_type=RUN_TIME,
                                             tc_cl_estab=120)

    test_thr.app_ccfg = App(app_proto=RAW_CLIENT,
                            app_raw_client=RawClient(rc_req_plen=5120,
                                                     rc_resp_plen=5120))
    test_thr.app_scfg = App(app_proto=RAW_SERVER,
                            app_raw_server=RawServer(rs_req_plen=5120,
                                                     rs_resp_plen=5120))

    test_thr.tc_init_delay = Delay(d_value=0)
    test_thr.tc_uptime = Delay(d_value=1)
    test_thr.tc_downtime = Delay(d_value=0)

    start_memory = env.get_memory()

    localenv.set_value(env.TCB_POOL_SZ, 98000)
    localenv.set_value(env.UCB_POOL_SZ, 0)

    out_folder = "/tmp/{}-test-{}/".format(test_tcp4_throughput.__name__,
                                           get_uniq_stamp())

    return [test_thr], start_memory, out_folder, localenv


def test_single_udp_throughput():
    """Configures a test that fulfill the 100Gb/s nic monodirectional"""
    localenv = Warp17Env('ut/ini/{}.ini'.format(socket.gethostname()))
    test_thr = Test()
    test_thr.cl_port = 0
    test_thr.sr_port = 1
    test_thr.add_l3(test_thr.cl_port, 167837697, 1)  # 10.1.0.1
    test_thr.add_l3(test_thr.sr_port, 167772161, 15)  # 10.0.0.1-10.0.0.15
    test_thr.l4_config[test_thr.cl_port] = 15
    test_thr.l4_config[test_thr.sr_port] = 50000  # not really needed
    test_thr.proto = UDP

    test_thr.cl_test_criteria = TestCriteria(tc_crit_type=RUN_TIME,
                                             tc_cl_estab=120)

    test_thr.app_ccfg = App(app_proto=RAW_CLIENT,
                            app_raw_client=RawClient(rc_req_plen=32768,
                                                     rc_resp_plen=0))
    test_thr.app_scfg = App(app_proto=RAW_SERVER,
                            app_raw_server=RawServer(rs_req_plen=0,
                                                     rs_resp_plen=0))

    start_memory = env.get_memory()

    localenv.set_value(env.TCB_POOL_SZ, 0)
    localenv.set_value(env.UCB_POOL_SZ, 98000)

    out_folder = "/tmp/{}-test-{}/".format(
        test_single_udp_throughput.__name__, get_uniq_stamp())

    return [test_thr], start_memory, out_folder, localenv


def test_throughput2():
    """Configures a test that fulfill the 100Gb/s nic"""
    localenv = Warp17Env('ut/ini/{}.ini'.format(socket.gethostname()))

    test_thr_cl1 = Test(type=TestCaseType.Value('CLIENT'), port=0, id=0)
    test_thr_cl1.cl_port = 0
    test_thr_cl1.sr_port = 1
    test_thr_cl1.add_l3(test_thr_cl1.cl_port, 167837697, 1)  # 10.1.0.1
    test_thr_cl1.add_l3(test_thr_cl1.sr_port, 167772161,
                        10)  # 10.0.0.1-10.0.0.10
    test_thr_cl1.l4_config[test_thr_cl1.cl_port] = 10
    test_thr_cl1.l4_config[test_thr_cl1.sr_port] = 50000  # not really needed
    test_thr_cl1.proto = UDP

    test_thr_cl1.cl_test_criteria = TestCriteria(tc_crit_type=RUN_TIME,
                                                 tc_cl_estab=120)

    test_thr_cl1.app_ccfg = App(app_proto=RAW_CLIENT,
                                app_raw_client=RawClient(rc_req_plen=80000,
                                                         rc_resp_plen=80000))
    test_thr_cl1.tc_init_delay = Delay(d_value=0)
    test_thr_cl1.tc_uptime = Delay(d_value=1)
    test_thr_cl1.tc_downtime = Delay(d_value=0)

    test_thr_cl2 = Test(type=TestCaseType.Value('CLIENT'),
                        port=1,
                        id=0)
    test_thr_cl2.cl_port = 1
    test_thr_cl2.sr_port = 0
    test_thr_cl2.add_l3(test_thr_cl2.cl_port, 167837697, 1)  # 10.1.0.1
    test_thr_cl2.add_l3(test_thr_cl2.sr_port, 167772161, 10)  # 10.0.0.1-10.0.0.10
    test_thr_cl2.l4_config[test_thr_cl2.cl_port] = 10
    test_thr_cl2.l4_config[test_thr_cl2.sr_port] = 50000  # not really needed
    test_thr_cl2.proto = UDP

    test_thr_cl2.cl_test_criteria = TestCriteria(tc_crit_type=RUN_TIME,
                                                 tc_cl_estab=120)

    test_thr_cl2.app_ccfg = App(app_proto=RAW_CLIENT,
                                app_raw_client=RawClient(rc_req_plen=80000,
                                                         rc_resp_plen=0))

    test_thr_cl2.init_delay = Delay(d_value=0)
    test_thr_cl2.uptime = Delay(d_value=1)
    test_thr_cl2.downtime = Delay(d_value=0)

    start_memory = env.get_memory()

    localenv.set_value(env.TCB_POOL_SZ, 0)
    localenv.set_value(env.UCB_POOL_SZ, 95000)

    out_folder = "/tmp/{}-test-{}/".format(test_throughput2.__name__,
                                           get_uniq_stamp())

    return [test_thr_cl1, test_thr_cl2], start_memory, out_folder, localenv


def test_tcp_single_client():
    """Configures a test that fulfill the 100Gb/s nic"""
    localenv = Warp17Env('ut/ini/{}.ini'.format(socket.gethostname()))

    test_thr_cl = Test(type=TestCaseType.Value('CLIENT'), port=0, id=0)
    test_thr_cl.cl_port = 0
    test_thr_cl.sr_port = 1
    test_thr_cl.add_l3(test_thr_cl.cl_port, 167837697, 4)  # 10.1.0.1
    test_thr_cl.add_l3(test_thr_cl.sr_port, 167772161, 1)  # 10.0.0.1-10.0.0.10
    test_thr_cl.l4_config[test_thr_cl.cl_port] = 200
    test_thr_cl.l4_config[test_thr_cl.sr_port] = 50000  # not really needed
    test_thr_cl.proto = TCP
    test_thr_cl.mtu = 2854
    test_thr_cl.tcpwin = 2560

    test_thr_cl.cl_test_criteria = TestCriteria(tc_crit_type=RUN_TIME,
                                                tc_cl_estab=120)

    test_thr_cl.app_ccfg = App(app_proto=RAW_CLIENT,
                               app_raw_client=RawClient(rc_req_plen=2560,
                                                        rc_resp_plen=2560))
    test_thr_cl.tc_init_delay = Delay(d_value=0)
    test_thr_cl.tc_uptime = Delay(d_value=1)
    test_thr_cl.tc_downtime = Delay(d_value=0)

    start_memory = env.get_memory()

    localenv.set_value(env.TCB_POOL_SZ, 0)
    localenv.set_value(env.UCB_POOL_SZ, 95000)

    out_folder = "/tmp/{}-test-{}/".format(test_tcp_single_client.__name__,
                                           get_uniq_stamp())

    return [test_thr_cl], start_memory, out_folder, localenv


def test_tcp_single_server():
    """Configures a test that fulfill the 100Gb/s nic"""
    localenv = Warp17Env('ut/ini/{}.ini'.format(socket.gethostname()))

    test_thr_srv = Test(type=TestCaseType.Value('SERVER'), port=0, id=0)
    test_thr_srv.sr_port = 0
    test_thr_srv.add_l3(test_thr_srv.sr_port, 167772161, 1)
    test_thr_srv.l4_config[test_thr_srv.sr_port] = 50000  # not really needed
    test_thr_srv.proto = TCP
    test_thr_srv.mtu = 2854
    test_thr_srv.tcpwin = 2560

    test_thr_srv.cl_test_criteria = TestCriteria(tc_crit_type=RUN_TIME,
                                                 tc_cl_estab=120)

    test_thr_srv.app_scfg = App(app_proto=RAW_SERVER,
                                app_raw_server=RawServer(rs_req_plen=2560,
                                                         rs_resp_plen=2560))

    test_thr_srv.tc_init_delay = Delay(d_value=0)
    test_thr_srv.tc_uptime = Delay(d_value=1)
    test_thr_srv.tc_downtime = Delay(d_value=0)

    start_memory = env.get_memory()

    localenv.set_value(env.TCB_POOL_SZ, 0)
    localenv.set_value(env.UCB_POOL_SZ, 95000)

    out_folder = "/tmp/{}-test-{}/".format(test_tcp_single_server.__name__,
                                           get_uniq_stamp())

    return [test_thr_srv], start_memory, out_folder, localenv


tests = []  # here you can append the tests you want to run (in sequence)
# tests.append(test_http_throughput())
# tests.append(test_tcp4_throughput())
# tests.append(test_udp_throughput())
# tests.append(test_tcp_single_server())
# tests.append(test_tcp_single_client())

for test, start_memory, out_folder, localenv in tests:
    res_file = "{}res.txt".format(out_folder)
    log_file = "{}out.log".format(out_folder)
    if not os.path.exists(out_folder):
        os.mkdir(out_folder)
    print "Logs and outputs in " + out_folder
    resultwriter = open(res_file, "w")
    resultwriter.write("Stats collection:_{}\n".format(datetime.today()))
    running_times = 10
    for i in range(0, running_times):
        print "run {}".format(i)
        resultwriter.write("Run {}\n".format(i))
        resultwriter.flush()
        collect_stats(resultwriter, localenv, test)
    resultwriter.write("Finish\n")
    resultwriter.close()
    sleep(20)  # waiting between each warp17 restart
