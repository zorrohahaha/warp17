/*
 * DO NOT ALTER OR REMOVE COPYRIGHT NOTICES OR THIS FILE HEADER
 *
 * Copyright (c) 2016, Juniper Networks, Inc. All rights reserved.
 *
 *
 * The contents of this file are subject to the terms of the BSD 3 clause
 * License (the "License"). You may not use this file except in compliance
 * with the License.
 *
 * You can obtain a copy of the license at
 * https://github.com/Juniper/warp17/blob/master/LICENSE.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice,
 * this list of conditions and the following disclaimer.
 *
 * 2. Redistributions in binary form must reproduce the above copyright
 * notice, this list of conditions and the following disclaimer in the
 * documentation and/or other materials provided with the distribution.
 *
 * 3. Neither the name of the copyright holder nor the names of its
 * contributors may be used to endorse or promote products derived from this
 * software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 *
 * File name:
 *     tpg_ipv4.c
 *
 * Description:
 *     IPv4 processing.
 *
 * Author:
 *     Dumitru Ceara, Eelco Chaudron
 *
 * Initial Created:
 *     03/03/2015
 *
 * Notes:
 *
 */

/*****************************************************************************
 * Include files
 ****************************************************************************/
#include "tcp_generator.h"

/*****************************************************************************
 * Global variables
 ****************************************************************************/
/* Define IPv4 global statistics. Each thread has its own set of locally
 * allocated stats which are accessible through STATS_GLOBAL(type, core, port).
 */
STATS_DEFINE(tpg_ipv4_statistics_t);

/*
 * DSCP value to name mapping.
 */
static const char *ipv4_dscp_names[IPV4_DSCP_MAX] = {
    [0x0A] = "af11",
    [0x0C] = "af12",
    [0x0E] = "af13",
    [0x12] = "af21",
    [0x14] = "af22",
    [0x16] = "af23",
    [0x1A] = "af31",
    [0x1C] = "af32",
    [0x1E] = "af33",
    [0x22] = "af41",
    [0x24] = "af42",
    [0x26] = "af43",
    [0x00] = "be",
    [0x08] = "cs1",
    [0x10] = "cs2",
    [0x18] = "cs3",
    [0x20] = "cs4",
    [0x28] = "cs5",
    [0x30] = "cs6",
    [0x38] = "cs7",
    [0x2E] = "ef",
};

/*
 * DSCP name to value mapping.
 */
static struct {
    const char *dscp_str;
    uint8_t     dscp_val;
} ipv4_dscp_values[] = {
    {.dscp_str = "af11", .dscp_val = 0x0A},
    {.dscp_str = "af12", .dscp_val = 0x0C},
    {.dscp_str = "af13", .dscp_val = 0x0E},
    {.dscp_str = "af21", .dscp_val = 0x12},
    {.dscp_str = "af22", .dscp_val = 0x14},
    {.dscp_str = "af23", .dscp_val = 0x16},
    {.dscp_str = "af31", .dscp_val = 0x1A},
    {.dscp_str = "af32", .dscp_val = 0x1C},
    {.dscp_str = "af33", .dscp_val = 0x1E},
    {.dscp_str = "af41", .dscp_val = 0x22},
    {.dscp_str = "af42", .dscp_val = 0x24},
    {.dscp_str = "af43", .dscp_val = 0x26},
    {.dscp_str = "be",   .dscp_val = 0x00},
    {.dscp_str = "cs1",  .dscp_val = 0x08},
    {.dscp_str = "cs2",  .dscp_val = 0x10},
    {.dscp_str = "cs3",  .dscp_val = 0x18},
    {.dscp_str = "cs4",  .dscp_val = 0x20},
    {.dscp_str = "cs5",  .dscp_val = 0x28},
    {.dscp_str = "cs6",  .dscp_val = 0x30},
    {.dscp_str = "cs7",  .dscp_val = 0x38},
    {.dscp_str = "ef",   .dscp_val = 0x2E},
};

/*
 * ECN value to name mapping.
 */
static const char *ipv4_ecn_names[IPv4_ECN_MAX] = {
    [0x0] = "Non-ECT",
    [0x1] = "ECT1",
    [0x2] = "ECT0",
    [0x3] = "CE",
};

/*
 * ECN name to value mapping.
 */
static struct {
    const char *ecn_str;
    uint8_t     ecn_val;
} ipv4_ecn_values[] = {
    {.ecn_str = "Non-ECT", .ecn_val = 0x0},
    {.ecn_str = "ECT0",    .ecn_val = 0x2},
    {.ecn_str = "ECT1",    .ecn_val = 0x1},
    {.ecn_str = "CE",      .ecn_val = 0x3},
};

/*****************************************************************************
 * CLI commands
 *****************************************************************************
 * - "show ipv4 statistics {details}"
 ****************************************************************************/
struct cmd_show_ipv4_statistics_result {
    cmdline_fixed_string_t show;
    cmdline_fixed_string_t ipv4;
    cmdline_fixed_string_t statistics;
    cmdline_fixed_string_t details;
};

static cmdline_parse_token_string_t cmd_show_ipv4_statistics_T_show =
    TOKEN_STRING_INITIALIZER(struct cmd_show_ipv4_statistics_result, show, "show");
static cmdline_parse_token_string_t cmd_show_ipv4_statistics_T_ipv4 =
    TOKEN_STRING_INITIALIZER(struct cmd_show_ipv4_statistics_result, ipv4, "ipv4");
static cmdline_parse_token_string_t cmd_show_ipv4_statistics_T_statistics =
    TOKEN_STRING_INITIALIZER(struct cmd_show_ipv4_statistics_result, statistics, "statistics");
static cmdline_parse_token_string_t cmd_show_ipv4_statistics_T_details =
    TOKEN_STRING_INITIALIZER(struct cmd_show_ipv4_statistics_result, details, "details");

static void cmd_show_ipv4_statistics_parsed(void *parsed_result __rte_unused,
                                            struct cmdline *cl,
                                            void *data)
{
    int port;
    int option = (intptr_t) data;

    for (port = 0; port < rte_eth_dev_count(); port++) {

        /*
         * Calculate totals first
         */
        tpg_ipv4_statistics_t total_stats;

        test_mgmt_get_ipv4_stats(port, &total_stats, NULL);

        /*
         * Display individual counters
         */
        cmdline_printf(cl, "Port %d IPv4 statistics:\n", port);

        SHOW_64BIT_STATS("Received Packets", tpg_ipv4_statistics_t,
                         ips_received_pkts,
                         port,
                         option);

        SHOW_64BIT_STATS("Received Bytes", tpg_ipv4_statistics_t,
                         ips_received_bytes,
                         port,
                         option);

        cmdline_printf(cl, "\n");

        SHOW_64BIT_STATS("Received ICMP", tpg_ipv4_statistics_t,
                         ips_protocol_icmp,
                         port,
                         option);

        SHOW_64BIT_STATS("Received TCP ", tpg_ipv4_statistics_t,
                         ips_protocol_tcp,
                         port,
                         option);

        SHOW_64BIT_STATS("Received UDP ", tpg_ipv4_statistics_t,
                         ips_protocol_udp,
                         port,
                         option);

        SHOW_64BIT_STATS("Received other ", tpg_ipv4_statistics_t,
                         ips_protocol_other,
                         port,
                         option);

        cmdline_printf(cl, "\n");


        SHOW_32BIT_STATS("Invalid checksum", tpg_ipv4_statistics_t,
                         ips_invalid_checksum,
                         port,
                         option);

        SHOW_32BIT_STATS("Small mbuf fragment", tpg_ipv4_statistics_t,
                         ips_to_small_fragment,
                         port,
                         option);

        SHOW_32BIT_STATS("IP hdr to small", tpg_ipv4_statistics_t,
                         ips_hdr_to_small,
                         port,
                         option);

        SHOW_32BIT_STATS("Total length invalid", tpg_ipv4_statistics_t,
                         ips_total_length_invalid,
                         port,
                         option);

        SHOW_32BIT_STATS("Received Fragments", tpg_ipv4_statistics_t,
                         ips_received_frags,
                         port,
                         option);

#ifndef _SPEEDY_PKT_PARSE_
        SHOW_32BIT_STATS("Invalid version:", tpg_ipv4_statistics_t,
                         ips_not_v4,
                         port,
                         option);

        SHOW_32BIT_STATS("Reserved bit set:", tpg_ipv4_statistics_t,
                         ips_reserved_bit_set,
                         port,
                         option);
#endif

        SHOW_32BIT_STATS("Invalid Padding:", tpg_ipv4_statistics_t,
                         ips_invalid_pad,
                         port,
                         option);

        cmdline_printf(cl, "\n");
    }

}

cmdline_parse_inst_t cmd_show_ipv4_statistics = {
    .f = cmd_show_ipv4_statistics_parsed,
    .data = NULL,
    .help_str = "show ipv4 statistics",
    .tokens = {
        (void *)&cmd_show_ipv4_statistics_T_show,
        (void *)&cmd_show_ipv4_statistics_T_ipv4,
        (void *)&cmd_show_ipv4_statistics_T_statistics,
        NULL,
    },
};

cmdline_parse_inst_t cmd_show_ipv4_statistics_details = {
    .f = cmd_show_ipv4_statistics_parsed,
    .data = (void *) (intptr_t) 'd',
    .help_str = "show ipv4 statistics details",
    .tokens = {
        (void *)&cmd_show_ipv4_statistics_T_show,
        (void *)&cmd_show_ipv4_statistics_T_ipv4,
        (void *)&cmd_show_ipv4_statistics_T_statistics,
        (void *)&cmd_show_ipv4_statistics_T_details,
        NULL,
    },
};

/*****************************************************************************
 * Main menu context
 ****************************************************************************/
static cmdline_parse_ctx_t cli_ctx[] = {
    &cmd_show_ipv4_statistics,
    &cmd_show_ipv4_statistics_details,
    NULL,
};

/*****************************************************************************
 * ipv4_init()
 ****************************************************************************/
bool ipv4_init(void)
{
    /*
     * Add port module CLI commands
     */
    if (!cli_add_main_ctx(cli_ctx)) {
        RTE_LOG(ERR, USER1, "ERROR: Can't add IPv4 specific CLI commands!\n");
        return false;
    }

    /*
     * Allocate memory for IPv4 statistics, and clear all of them
     */
    if (STATS_GLOBAL_INIT(tpg_ipv4_statistics_t, "ipv4_stats") == NULL) {
        RTE_LOG(ERR, USER1,
                "ERROR: Failed allocating IPv4 statistics memory!\n");
        return false;
    }

    return true;
}

/*****************************************************************************
 * ipv4_lcore_init()
 ****************************************************************************/
void ipv4_lcore_init(uint32_t lcore_id)
{
    /* Init the local stats. */
    if (STATS_LOCAL_INIT(tpg_ipv4_statistics_t,
                         "ipv4_stats", lcore_id) == NULL) {
        TPG_ERROR_ABORT("[%d:%s() Failed to allocate per lcore ipv4_stats!\n",
                        rte_lcore_index(lcore_id),
                        __func__);
    }
}

/*****************************************************************************
 * ipv4_store_sockopt()
 ****************************************************************************/
void ipv4_store_sockopt(ipv4_sockopt_t *dest, const tpg_ipv4_sockopt_t *options)
{
    dest->io_tos = options->io_tos;
}

/*****************************************************************************
 * ipv4_load_sockopt()
 ****************************************************************************/
void ipv4_load_sockopt(tpg_ipv4_sockopt_t *dest, const ipv4_sockopt_t *options)
{
    dest->io_tos = options->io_tos;
    dest->has_io_tos = true;
}

/*****************************************************************************
 * ipv4_tos_to_dscp_name()
 ****************************************************************************/
const char *ipv4_tos_to_dscp_name(const tpg_ipv4_sockopt_t *options)
{
    const char *dscp_name;

    dscp_name = ipv4_dscp_names[IPV4_TOS_TO_DSCP(options->io_tos)];

    if (!dscp_name)
        return "UNK";

    return dscp_name;
}

/*****************************************************************************
 * ipv4_tos_to_ecn_name()
 ****************************************************************************/
const char *ipv4_tos_to_ecn_name(const tpg_ipv4_sockopt_t *options)
{
    return ipv4_ecn_names[IPV4_TOS_TO_ECN(options->io_tos)];
}

/*****************************************************************************
 * ipv4_dscp_ecn_to_tos()
 ****************************************************************************/
uint8_t ipv4_dscp_ecn_to_tos(const char *dscp_str, const char *ecn_str)
{
    uint32_t i;
    uint8_t  dscp = IPV4_TOS_INVALID;
    uint8_t  ecn = IPV4_TOS_INVALID;

    for (i = 0;
         i < (sizeof(ipv4_dscp_values) / sizeof(ipv4_dscp_values[0]));
         i++) {

        if (strncasecmp(dscp_str, ipv4_dscp_values[i].dscp_str,
                        strlen(ipv4_dscp_values[i].dscp_str) + 1) == 0) {
            dscp = ipv4_dscp_values[i].dscp_val;
            break;
        }
    }

    if (dscp == IPV4_TOS_INVALID)
        return IPV4_TOS_INVALID;

    for (i = 0;
         i < (sizeof(ipv4_ecn_values) / sizeof(ipv4_ecn_values[0]));
         i++) {

        if (strncasecmp(ecn_str, ipv4_ecn_values[i].ecn_str,
                        strlen(ipv4_ecn_values[i].ecn_str) + 1) == 0) {
            ecn = ipv4_ecn_values[i].ecn_val;
            break;
        }
    }

    if (ecn == IPV4_TOS_INVALID)
        return IPV4_TOS_INVALID;

    return IPV4_TOS(dscp, ecn);
}

/*****************************************************************************
 * ipv4_build_ipv4_hdr()
 ****************************************************************************/
int ipv4_build_ipv4_hdr(sockopt_t *sockopt,
                        struct rte_mbuf *mbuf, uint32_t src_addr,
                        uint32_t dst_addr, uint8_t protocol,
                        uint16_t l4_len,
                        struct ipv4_hdr *hdr)
{
    /*
     * TODO: For now we do not support options.
     */

    uint16_t         ip_hdr_len = sizeof(struct ipv4_hdr);
    struct ipv4_hdr *ip_hdr;

    if (hdr != NULL)
        TPG_ERROR_ABORT("TODO: %s!\n", "No reference header supported");

    ip_hdr = (struct ipv4_hdr *) rte_pktmbuf_append(mbuf, ip_hdr_len);

    if (ip_hdr == NULL)
        return -ENOMEM;

    ip_hdr->version_ihl = (4 << 4) | (ip_hdr_len >> 2);
    ip_hdr->type_of_service = sockopt->so_ipv4.io_tos;
    ip_hdr->total_length = rte_cpu_to_be_16(ip_hdr_len + l4_len);
    ip_hdr->packet_id = rte_rand();
    ip_hdr->fragment_offset = rte_cpu_to_be_16(0);
    ip_hdr->time_to_live = 60;
    ip_hdr->next_proto_id = protocol;
    ip_hdr->src_addr = rte_cpu_to_be_32(src_addr);
    ip_hdr->dst_addr = rte_cpu_to_be_32(dst_addr);

#if !defined(TPG_SW_CHECKSUMMING)
    if (true) {
#else
    if (sockopt->so_eth.ethso_tx_offload_ipv4_cksum) {
#endif
        /*
         * We assume hardware checksum calculation
         */
        mbuf->l3_len = ip_hdr_len;
        mbuf->ol_flags |= PKT_TX_IP_CKSUM;
        ip_hdr->hdr_checksum = 0;
    } else {
        ip_hdr->hdr_checksum = 0;
        /* TODO: This call does not work if options are present!! */
        ip_hdr->hdr_checksum = rte_ipv4_cksum(ip_hdr);
    }

    return sizeof(struct ipv4_hdr);
}


/*****************************************************************************
 * ipv4_receive_pkt()
 *
 * Return the mbuf only if it needs to be free'ed back to the pool, if it was
 * consumed, or needed later (ip refrag), return NULL.
 ****************************************************************************/
struct rte_mbuf *ipv4_receive_pkt(packet_control_block_t *pcb,
                                  struct rte_mbuf *mbuf)
{
    unsigned int           ip_hdr_len;
    tpg_ipv4_statistics_t *stats;
    struct ipv4_hdr       *ip_hdr;

    stats = STATS_LOCAL(tpg_ipv4_statistics_t, pcb->pcb_port);

    if (unlikely(rte_pktmbuf_data_len(mbuf) < sizeof(struct ipv4_hdr))) {
        RTE_LOG(DEBUG, USER2, "[%d:%s()] ERR: mbuf fragment to small for ipv4_hdr!\n",
                pcb->pcb_core_index, __func__);
        INC_STATS(stats, ips_to_small_fragment);
        return mbuf;
    }

    ip_hdr = rte_pktmbuf_mtod(mbuf, struct ipv4_hdr *);
    ip_hdr_len = (ip_hdr->version_ihl & 0x0F) << 2;

    PKT_TRACE(pcb, IPV4, DEBUG, "src/dst=%8.8X/%8.8X, prot=%u, hdrlen=%d, len=%u",
              rte_be_to_cpu_32(ip_hdr->src_addr),
              rte_be_to_cpu_32(ip_hdr->dst_addr),
              ip_hdr->next_proto_id,
              ip_hdr_len,
              rte_be_to_cpu_16(ip_hdr->total_length));

    PKT_TRACE(pcb, IPV4, DEBUG, " ttl=%u, tos=%u, frag=0x%4.4X[%c%c%c], id=0x%4.4X, csum=0x%4.4X",
              ip_hdr->time_to_live,
              ip_hdr->type_of_service,
              rte_be_to_cpu_16(ip_hdr->fragment_offset) & IPV4_HDR_OFFSET_MASK,
              (rte_be_to_cpu_16(ip_hdr->fragment_offset) & 1<<15) == 0 ? '-' : 'R',
              (rte_be_to_cpu_16(ip_hdr->fragment_offset) & IPV4_HDR_DF_FLAG) == 0 ? '-' : 'd',
              (rte_be_to_cpu_16(ip_hdr->fragment_offset) & IPV4_HDR_MF_FLAG) == 0 ? '-' : 'm',
              rte_be_to_cpu_16(ip_hdr->packet_id),
              rte_be_to_cpu_16(ip_hdr->hdr_checksum));

    /*
     * TODO: We don't support IP fragments yet so inc counter and drop.
     */
    if (unlikely((rte_be_to_cpu_16(ip_hdr->fragment_offset) & IPV4_HDR_MF_FLAG) ||
                 (rte_be_to_cpu_16(ip_hdr->fragment_offset) & IPV4_HDR_OFFSET_MASK))) {
        INC_STATS(stats, ips_received_frags);
        return mbuf;
    }


    /*
     * Update stats
     */

    INC_STATS(stats, ips_received_pkts);
    INC_STATS_VAL(stats, ips_received_bytes,
                  rte_be_to_cpu_16(ip_hdr->total_length));

    switch (ip_hdr->next_proto_id) {
    case IPPROTO_TCP:
        INC_STATS(stats, ips_protocol_tcp);
        break;
    case IPPROTO_UDP:
        INC_STATS(stats, ips_protocol_udp);
        break;
    case IPPROTO_ICMP:
        INC_STATS(stats, ips_protocol_icmp);
        break;
    default:
        INC_STATS(stats, ips_protocol_other);
        break;
    }

    /*
     * Check header content, and buffer space
     */
    if (unlikely(rte_pktmbuf_data_len(mbuf) < ip_hdr_len)) {
        RTE_LOG(DEBUG, USER2, "[%d:%s()] ERR: mbuf fragment to small for ipv4 header!\n",
                pcb->pcb_core_index, __func__);

        INC_STATS(stats, ips_to_small_fragment);
        return mbuf;
    }

    if (unlikely(ip_hdr_len < sizeof(struct ipv4_hdr))) {
        RTE_LOG(DEBUG, USER2, "[%d:%s()] ERR: IP hdr len smaller than header!\n",
                pcb->pcb_core_index, __func__);

        INC_STATS(stats, ips_hdr_to_small);
        return mbuf;
    }

    if (unlikely(rte_be_to_cpu_16(ip_hdr->total_length) < ip_hdr_len ||
                 rte_be_to_cpu_16(ip_hdr->total_length) > rte_pktmbuf_pkt_len(mbuf))) {

        RTE_LOG(DEBUG, USER2, "[%d:%s()] ERR: IP total lenght invalid!\n",
                pcb->pcb_core_index, __func__);

        INC_STATS(stats, ips_total_length_invalid);
        return mbuf;
    }

#ifndef _SPEEDY_PKT_PARSE_
    /*
     * If speedy is set we assume HW takes care of this ;)
     */
    if (unlikely((ip_hdr->version_ihl & 0xF0) != 0x40)) {
        RTE_LOG(DEBUG, USER2, "[%d:%s()] ERR: Packet version is not IPv4!\n",
                pcb->pcb_core_index, __func__);

        INC_STATS(stats, ips_not_v4);
        return mbuf;
    }
    if (unlikely((rte_be_to_cpu_16(ip_hdr->fragment_offset) & 1<<15) != 0)) {
        /* No log message for this, some one might actually set the evil bit ;) */
        INC_STATS(stats, ips_reserved_bit_set);
    }

    if (PKT_TRACE_ENABLED(pcb)) {
        unsigned int  i;
        uint32_t     *options = (uint32_t *) (ip_hdr + 1);

        for (i = 0;
             i < ((ip_hdr_len - sizeof(struct ipv4_hdr)) / sizeof(uint32_t));
             i++) {

            PKT_TRACE(pcb, IPV4, DEBUG, "  option word 0x%2.2X: 0x%8.8X",
                      i,
                      rte_be_to_cpu_32(options[i]));
        }
    }

#endif

    /*
     * Handle checksum...
     */

#if !defined(TPG_SW_CHECKSUMMING)
    if (true) {
#else
    if ((RTE_PER_LCORE(local_port_dev_info)[pcb->pcb_port].pi_dev_info.rx_offload_capa &
         DEV_RX_OFFLOAD_IPV4_CKSUM) != 0) {
#endif
        if (unlikely((mbuf->ol_flags & PKT_RX_IP_CKSUM_BAD) != 0)) {
            RTE_LOG(DEBUG, USER2, "[%d:%s()] ERR: Invalid IPv4 checksum 0x%2.2X!\n",
                    pcb->pcb_core_index, __func__, ip_hdr->hdr_checksum);

            INC_STATS(stats, ips_invalid_checksum);
            return mbuf;
        }
    } else {
        /*
         * No HW checksum support do it manually...
         *
         * NOTE: rte_ipv4_cksum() has a bug as it ignores options if present.
         */
        uint16_t checksum;

        checksum = rte_raw_cksum(ip_hdr, ip_hdr_len);
        if (unlikely(checksum != 0xFFFF)) {
            RTE_LOG(DEBUG, USER2, "[%d:%s()] ERR: Invalid IPv4 checksum %2.2X!\n",
                    pcb->pcb_core_index, __func__, checksum);

            INC_STATS(stats, ips_invalid_checksum);
            return mbuf;
        }
    }

    /*
     * Update mbuf/pcb and send packet of to the protocol handler
     */

    pcb->pcb_ipv4 = ip_hdr;
    pcb->pcb_l4_len = rte_be_to_cpu_16(ip_hdr->total_length) - ip_hdr_len;
    rte_pktmbuf_adj(mbuf, ip_hdr_len);

    /* "Remove" packet padding (e.g. Ethernet). Applications might store the
     * mbuf (e.g. TCP) and it would be nice to be able to use pkt_len as the
     * real data size.
     */
    if (unlikely(mbuf->pkt_len > pcb->pcb_l4_len)) {
        if (unlikely(rte_pktmbuf_trim(mbuf,
                                      mbuf->pkt_len - pcb->pcb_l4_len) == -1)) {
            INC_STATS(stats, ips_invalid_pad);
            return mbuf;
        }
    }

    if (ip_hdr->next_proto_id == IPPROTO_TCP)
        return tcp_receive_pkt(pcb, mbuf);
    else if (ip_hdr->next_proto_id == IPPROTO_UDP)
        return udp_receive_pkt(pcb, mbuf);

    return mbuf;
}

