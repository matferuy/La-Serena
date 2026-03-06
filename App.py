    # --- PESTAÑA 1: DASHBOARD ---
    with tabs[0]:
        if not df_gastos.empty:
            df_dash = df_gastos.copy()
            df_dash['Fecha'] = pd.to_datetime(df_dash['Fecha'])
            
            # --- CÁLCULO DE KPIs ---
            total_uyu = df_dash["Monto_UYU"].sum()
            total_transacciones = len(df_dash)
            tasa_actual = obtener_tasa_usd_uyu()
            total_usd_estimado = total_uyu / tasa_actual if tasa_actual else 0
            
            # --- FILA 1: TARJETAS MÉTRICAS ---
            kpi1, kpi2, kpi3 = st.columns(3)
            with kpi1:
                st.markdown(f"""
                    <div class="kpi-card-blue">
                        <div class="kpi-title">Inversión (UYU)</div>
                        <div class="kpi-value">${total_uyu:,.0f}</div>
                        <div class="kpi-subtitle">Total acumulado oficial</div>
                    </div>
                """, unsafe_allow_html=True)
            with kpi2:
                st.markdown(f"""
                    <div class="kpi-card-green">
                        <div class="kpi-title">Estimado (USD)</div>
                        <div class="kpi-value">U$S {total_usd_estimado:,.0f}</div>
                        <div class="kpi-subtitle">Ref: 1 USD = ${tasa_actual} UYU</div>
                    </div>
                """, unsafe_allow_html=True)
            with kpi3:
                st.markdown(f"""
                    <div class="kpi-card-dynamic">
                        <div class="kpi-title" style="color: var(--text-color);">Comprobantes</div>
                        <div class="kpi-value" style="color: var(--text-color);">{total_transacciones}</div>
                        <div class="kpi-subtitle">Registros de compras</div>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # --- FILA 2: GRÁFICOS SECUNDARIOS (DOBLE COLUMNA) ---
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.markdown("#### 📊 En qué se gastó")
                gastos_cat = df_dash.groupby("Categoria")["Monto_UYU"].sum().reset_index()
                fig_pie = px.pie(gastos_cat, values='Monto_UYU', names='Categoria', hole=0.5, 
                                 color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(margin=dict(t=10, b=20, l=0, r=0), showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
                
            with col_chart2:
                st.markdown("#### 👥 Quién pagó (Gastos directos)")
                aportes_socio = df_dash.groupby("Pagado_por")["Monto_UYU"].sum().reset_index()
                fig_bar = px.bar(aportes_socio, x='Pagado_por', y='Monto_UYU', text_auto='.2s',
                                 color='Pagado_por', color_discrete_sequence=["#3B82F6", "#10B981", "#F59E0B"])
                fig_bar.update_layout(margin=dict(t=10, b=20, l=0, r=0), showlegend=False, 
                                      xaxis_title="", yaxis_title="Monto (UYU)", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})

            st.markdown("---")

            # --- FILA 3: RITMO DE GASTOS Y ÚLTIMOS MOVIMIENTOS ---
            st.markdown("#### 📈 Evolución del gasto en el tiempo")
            gastos_fecha = df_dash.groupby("Fecha")["Monto_UYU"].sum().reset_index()
            gastos_fecha = gastos_fecha.sort_values("Fecha")
            gastos_fecha["Gasto_Acumulado"] = gastos_fecha["Monto_UYU"].cumsum()
            
            # Cambiado a un gráfico de área para mejor impacto visual
            fig_area = px.area(gastos_fecha, x='Fecha', y='Gasto_Acumulado', markers=True, 
                               color_discrete_sequence=["#2563EB"])
            fig_area.update_layout(margin=dict(t=10, b=10, l=0, r=0), xaxis_title="", yaxis_title="Acumulado (UYU)", 
                                   paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_area, use_container_width=True, config={'displayModeBar': False})
            
            st.markdown("<br>#### 📌 Últimos 5 registros", unsafe_allow_html=True)
            df_ultimos = df_dash.sort_values("Fecha", ascending=False).head(5)
            
            # Formatear la tabla para que se vea limpia
            st.dataframe(
                df_ultimos[["Fecha", "Concepto", "Categoria", "Pagado_por", "Monto_UYU"]].style.format({
                    "Monto_UYU": "${:,.0f}"
                }),
                use_container_width=True,
                hide_index=True
            )
            
        else:
            st.info("Bienvenido. Registra tu primer gasto para ver los indicadores del proyecto.")
