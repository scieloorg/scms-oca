
/*
* Licensed to the Apache Software Foundation (ASF) under one
* or more contributor license agreements.  See the NOTICE file
* distributed with this work for additional information
* regarding copyright ownership.  The ASF licenses this file
* to you under the Apache License, Version 2.0 (the
* "License"); you may not use this file except in compliance
* with the License.  You may obtain a copy of the License at
*
*   http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing,
* software distributed under the License is distributed on an
* "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
* KIND, either express or implied.  See the License for the
* specific language governing permissions and limitations
* under the License.
*/

(function(root, factory) {
    if (typeof define === 'function' && define.amd) {
        // AMD. Register as an anonymous module.
        define(['exports', 'echarts'], factory);
    } else if (
        typeof exports === 'object' &&
        typeof exports.nodeName !== 'string'
    ) {
        // CommonJS
        factory(exports, require('echarts/lib/echarts'));
    } else {
        // Browser globals
        factory({}, root.echarts);
    }
})(this, function(exports, echarts) {
    var log = function(msg) {
        if (typeof console !== 'undefined') {
            console && console.error && console.error(msg);
        }
    };
    if (!echarts) {
        log('ECharts is not Loaded');
        return;
    }

    var colorPalette = [
        '#E01F54',
        '#6f5553',
        '#f5994e',
        '#b6a2de',
        '#6699FF',
        '#d3758f',
        '#8d98b3',
        '#38b6b6',
        '#59678c',
        '#60C0DD',
        '#ff6347',
        '#97b552',
        '#a4d8c2',
        '#f3f39d',
        '#e7dac9',
        '#7eb00a',
        '#F3A43B',
        '#5ab1ef',
        '#B5C334',
        '#D7504B',
        '#c8e49c',
        '#2e4783',
        '#d87a80',
        '#001852',
        '#9BCA63',
        '#2ec7c9',
        '#ffb980',
        '#F4E001',
        '#a092f1',
        '#E87C25',
        '#3cb371',
        '#0a915d',
        '#c05050',
        '#d5b158',
        '#FE8463',
        '#26C0C0',
        '#F0805A',
        '#ff6666',
        '#e5cf0d',
        '#ed9678',
        '#f3d999',
        '#f16d7a',
        '#dcc392',
        '#dc69aa',
        '#95706d',
        '#c9ab00',
        '#c14089',
        '#FAD860',
        '#07a2a4',
        '#C1232B',
        '#c6b38e',
        '#b8d2c7',
        '#FCCE10',
        '#eaf889',
        '#27727B',
        '#9a7fd1',
        '#C6E579',
        '#82b6e9',
        '#f5e8c8',
        '#588dd5',
        '#cb8e85',
        '#eaf889'
    ];

    var theme = {
        color: colorPalette,

        visualMap: {
            color: ['#e01f54', '#e7dbc3'],
            textStyle: {
                color: '#333'
            }
        },

        candlestick: {
            itemStyle: {
                color: '#e01f54',
                color0: '#001852'
            },
            lineStyle: {
                width: 1,
                color: '#f5e8c8',
                color0: '#b8d2c7'
            },
            areaStyle: {
                color: '#a4d8c2',
                color0: '#f3d999'
            }
        },

        graph: {
            itemStyle: {
                color: '#a4d8c2'
            },
            linkStyle: {
                color: '#f3d999'
            }
        },

        gauge: {
            axisLine: {
                lineStyle: {
                    color: [
                        [0.2, '#E01F54'],
                        [0.8, '#b8d2c7'],
                        [1, '#001852']
                    ],
                    width: 8
                }
            }
        }
    };

    echarts.registerTheme('roma-macarons-macarons2-infographic', theme);
});
