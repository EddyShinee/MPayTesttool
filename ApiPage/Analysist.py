import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from bs4 import BeautifulSoup
from datetime import datetime
import time
import re


def parse_html_table(html_content):
    """Parse HTML table from response and convert to DataFrame"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find the table
        table = soup.find('table', class_='table')
        if not table:
            st.error("❌ Could not find table in HTML response")
            return None
        
        # Find all rows
        rows = table.find_all('tr')
        if len(rows) < 2:
            st.warning("⚠️ No data rows found in table")
            return None
        
        # Extract headers
        headers = []
        data_rows = []
        
        # Find header row (look for row with td.header)
        header_row = None
        for row in rows:
            if row.find('td', class_='header'):
                header_row = row
                break
        
        if header_row:
            header_cells = header_row.find_all('td', class_='header')
            headers = []
            for cell in header_cells:
                label = cell.find('label')
                if label:
                    headers.append(label.get_text(strip=True))
                else:
                    headers.append(cell.get_text(strip=True))
        
        # Extract data rows (rows with td.border and td.last-border)
        processed_rows = set()  # Track processed rows to avoid duplicates
        for row in rows:
            border_cells = row.find_all('td', class_='border')
            last_border_cell = row.find('td', class_='last-border')
            
            if len(border_cells) > 0:
                row_data = []
                # Add all border cells
                for cell in border_cells:
                    label = cell.find('label')
                    if label:
                        row_data.append(label.get_text(strip=True))
                    else:
                        row_data.append(cell.get_text(strip=True))
                
                # Add last-border cell if exists
                if last_border_cell:
                    last_label = last_border_cell.find('label')
                    if last_label:
                        row_data.append(last_label.get_text(strip=True))
                    else:
                        row_data.append(last_border_cell.get_text(strip=True))
                
                # Only add if row has data (not empty) and not already processed
                if any(cell.strip() for cell in row_data):
                    row_id = id(row)
                    if row_id not in processed_rows:
                        data_rows.append(row_data)
                        processed_rows.add(row_id)
        
        if not data_rows:
            st.warning("⚠️ No data rows found")
            return None
        
        # Create DataFrame
        # Adjust headers to match data columns if needed
        if headers and len(headers) != len(data_rows[0]) if data_rows else 0:
            # Try to match headers with data
            if len(headers) < len(data_rows[0]):
                # Add missing headers
                for i in range(len(headers), len(data_rows[0])):
                    headers.append(f'Column_{i+1}')
            elif len(headers) > len(data_rows[0]):
                # Truncate headers
                headers = headers[:len(data_rows[0])]
        
        if not headers:
            headers = [f'Column_{i+1}' for i in range(len(data_rows[0]) if data_rows else 0)]
        
        df = pd.DataFrame(data_rows, columns=headers[:len(data_rows[0])] if data_rows else [])
        
        return df
        
    except Exception as e:
        st.error(f"❌ Error parsing HTML: {str(e)}")
        st.exception(e)
        return None


def parse_datetime(date_str):
    """Parse datetime string in format DD/MM/YYYY HH:MM:SS"""
    try:
        # Handle format: 24/12/2025 15:29:06
        return pd.to_datetime(date_str, format='%d/%m/%Y %H:%M:%S', errors='coerce')
    except:
        return None


def render_analysist():
    st.title("📊 Transaction Analysis")
    
    # Input fields
    col1, col2 = st.columns([1, 1])
    
    with col1:
        default_url = "https://my.2c2p.com/2.0/Transaction/PrintSearchTransactionV2"
        api_url = st.text_input(
            "🌐 API URL",
            value=default_url,
            help="Enter the API endpoint URL"
        )
    
    with col2:
        session_id = st.text_input(
            "🔑 Session ID",
            value="",
            help="Enter ASP.NET_SessionId value",
            type="default"
        )
    
    # Send request button
    if st.button("🚀 Send Request", type="primary"):
        if not session_id:
            st.warning("⚠️ Please enter Session ID")
        elif not api_url:
            st.warning("⚠️ Please enter API URL")
        else:
            try:
                with st.spinner("🔄 Sending request..."):
                    # Prepare cookies
                    cookies = {
                        'ASP.NET_SessionId': session_id
                    }
                    
                    # Prepare headers
                    headers = {
                        'Cookie': f'ASP.NET_SessionId={session_id}'
                    }
                    
                    # Send POST request with empty data
                    start_time = time.time()
                    response = requests.get(
                        api_url,
                        headers=headers,
                        cookies=cookies,
                        data='',
                        timeout=120
                    )
                    elapsed = round(time.time() - start_time, 2)
                    
                    # Store response
                    st.session_state['analysist_response'] = response.text
                    st.session_state['analysist_status'] = response.status_code
                    st.session_state['analysist_elapsed'] = elapsed
                    
                    if response.status_code == 200:
                        st.success(f"✅ Request successful in {elapsed} seconds")
                        st.toast(f"✅ Request successful", icon="✅")
                    else:
                        st.error(f"❌ Request failed with HTTP {response.status_code}")
                        st.toast(f"❌ Request failed", icon="❌")
                        
            except requests.exceptions.Timeout:
                st.error("❌ Request timeout (120s)")
            except requests.exceptions.ConnectionError:
                st.error("❌ Connection error. Please check your network.")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.exception(e)
    
    # Display response and analysis
    if 'analysist_response' in st.session_state:
        response_text = st.session_state.get('analysist_response', '')
        status_code = st.session_state.get('analysist_status', 0)
        elapsed = st.session_state.get('analysist_elapsed', 0)
        
        if status_code == 200 and response_text:
            # Parse HTML table
            df = parse_html_table(response_text)
            
            if df is not None and not df.empty:
                st.markdown("---")
                st.header("📋 Transaction Data")
                
                # Display basic info
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Transactions", len(df))
                with col2:
                    st.metric("Response Time", f"{elapsed}s")
                with col3:
                    st.metric("Status Code", status_code)
                
                # Check if Date/Time column exists
                datetime_col = None
                for col in df.columns:
                    if 'date' in col.lower() and 'time' in col.lower():
                        datetime_col = col
                        break
                
                # Find Status column
                status_col = None
                for col in df.columns:
                    if 'status' in col.lower():
                        status_col = col
                        break
                
                # Find Transaction Amount column
                amount_col = None
                for col in df.columns:
                    if 'transaction amount' in col.lower() or 'amount' in col.lower():
                        amount_col = col
                        break
                
                if datetime_col:
                    # Parse datetime
                    df['ParsedDateTime'] = df[datetime_col].apply(parse_datetime)
                    df = df.dropna(subset=['ParsedDateTime'])
                    
                    if not df.empty:
                        # Extract date, hour, minute
                        df['Date'] = df['ParsedDateTime'].dt.date
                        df['Hour'] = df['ParsedDateTime'].dt.hour
                        df['Minute'] = df['ParsedDateTime'].dt.minute
                        
                        # Clean Status column if exists
                        if status_col:
                            df['Status'] = df[status_col].str.strip()
                        
                        # Clean Transaction Amount if exists
                        if amount_col:
                            df['Transaction Amount'] = df[amount_col].astype(str).str.replace(',', '').str.replace(' ', '')
                            df['Transaction Amount'] = pd.to_numeric(df['Transaction Amount'], errors='coerce')
                        
                        # ========== Profile Report Information ==========
                        st.markdown("---")
                        st.header("📋 Profile Report Information")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("Total Transactions", len(df))
                        
                        with col2:
                            if amount_col:
                                total_amount = df['Transaction Amount'].sum()
                                st.metric("Total Amount", f"{total_amount:,.0f} VND" if not pd.isna(total_amount) else "N/A")
                            else:
                                st.metric("Total Amount", "N/A")
                        
                        with col3:
                            if status_col:
                                approved_count = len(df[df['Status'] == 'Approved'])
                                st.metric("Approved", approved_count)
                            else:
                                st.metric("Approved", "N/A")
                        
                        with col4:
                            if status_col:
                                rejected_count = len(df[df['Status'] == 'Rejected'])
                                st.metric("Rejected", rejected_count)
                            else:
                                st.metric("Rejected", "N/A")
                        
                        # Additional statistics
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("📊 Status Distribution")
                            if status_col:
                                status_counts = df['Status'].value_counts()
                                st.dataframe(status_counts.reset_index().rename(columns={'index': 'Status', 'Status': 'Count'}), use_container_width=True)
                            else:
                                st.info("Status column not found")
                        
                        with col2:
                            st.subheader("💰 Amount Statistics")
                            if amount_col:
                                amount_stats = df['Transaction Amount'].describe()
                                st.dataframe(amount_stats.to_frame().T, use_container_width=True)
                            else:
                                st.info("Transaction Amount column not found")
                        
                        # Date range
                        date_range = st.columns(2)
                        with date_range[0]:
                            st.info(f"📅 From: {df['ParsedDateTime'].min().strftime('%Y-%m-%d %H:%M:%S')}")
                        with date_range[1]:
                            st.info(f"📅 To: {df['ParsedDateTime'].max().strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        # ========== Number of Transactions by Status (with time filtering) ==========
                        if status_col:
                            st.markdown("---")
                            st.header("📈 Number of Transactions by Status")
                            
                            # Time filter selection
                            time_filter_type = st.radio(
                                "Select Time Filter",
                                ["Day", "Hour", "Minute"],
                                horizontal=True,
                                key="time_filter_count"
                            )
                            
                            # Reload button - Streamlit will automatically rerun when widget values change
                            st.button("🔄 Reload Chart", key="reload_count", help="Click to refresh the chart")
                            
                            # Group by selected time filter
                            if time_filter_type == "Day":
                                # Group by calendar day
                                group_col = 'Date'
                                x_label = 'Date'
                                df_group = df.copy()
                            elif time_filter_type == "Hour":
                                # Group by full date + hour (to avoid summing all days together)
                                df_group = df.copy()
                                df_group['DateHour'] = df_group['ParsedDateTime'].dt.strftime('%Y-%m-%d %H:00')
                                group_col = 'DateHour'
                                x_label = 'Date-Hour'
                            else:
                                # Group by full date + hour:minute
                                df_group = df.copy()
                                df_group['DateMinute'] = df_group['ParsedDateTime'].dt.strftime('%Y-%m-%d %H:%M')
                                group_col = 'DateMinute'
                                x_label = 'Date-Time (Minute)'
                            
                            # Count by status and time bucket
                            count_data = df_group.groupby([group_col, 'Status']).size().reset_index(name='Count')
                            
                            # Create bar chart with value labels on each column
                            fig_count = px.bar(
                                count_data,
                                x=group_col,
                                y='Count',
                                color='Status',
                                title=f'Number of Transactions by Status ({time_filter_type})',
                                labels={group_col: x_label, 'Count': 'Number of Transactions'},
                                barmode='group',
                                text='Count',
                            )
                            # Always show the full time bucket on x-axis (Date / Date-Hour / Date-Minute)
                            # Use fullData.name to get the Status name from the trace
                            hovertemplate = f"{x_label}: %{{x}}<br>Status: %{{fullData.name}}<br>Count: %{{y}}<extra></extra>"
                            
                            fig_count.update_traces(
                                textposition='outside',
                                hovertemplate=hovertemplate,
                            )
                            fig_count.update_layout(
                                xaxis_title=x_label,
                                yaxis_title='Number of Transactions',
                                height=500,
                                showlegend=True,
                                uniformtext_minsize=10,
                                uniformtext_mode='hide',
                            )
                            st.plotly_chart(fig_count, use_container_width=True)
                            
                            # Create line chart for Number of Transactions by Status
                            fig_count_line = px.line(
                                count_data,
                                x=group_col,
                                y='Count',
                                color='Status',
                                title=f'Number of Transactions by Status ({time_filter_type}) - Line Chart',
                                labels={group_col: x_label, 'Count': 'Number of Transactions'},
                                markers=True
                            )
                            hovertemplate_line_count = f"{x_label}: %{{x}}<br>Status: %{{fullData.name}}<br>Count: %{{y}}<extra></extra>"
                            
                            fig_count_line.update_traces(
                                hovertemplate=hovertemplate_line_count
                            )
                            fig_count_line.update_layout(
                                xaxis_title=x_label,
                                yaxis_title='Number of Transactions',
                                height=500,
                                showlegend=True
                            )
                            st.plotly_chart(fig_count_line, use_container_width=True)

                            # Create stacked area chart for Number of Transactions by Status
                            fig_count_area = px.area(
                                count_data,
                                x=group_col,
                                y='Count',
                                color='Status',
                                title=f'Number of Transactions by Status ({time_filter_type}) - Stacked Area',
                                labels={group_col: x_label, 'Count': 'Number of Transactions'},
                            )
                            hovertemplate_area_count = f"{x_label}: %{{x}}<br>Status: %{{fullData.name}}<br>Count: %{{y}}<extra></extra>"
                            
                            fig_count_area.update_traces(
                                hovertemplate=hovertemplate_area_count,
                                mode='lines',
                            )
                            fig_count_area.update_layout(
                                xaxis_title=x_label,
                                yaxis_title='Number of Transactions',
                                height=500,
                                showlegend=True,
                            )
                            st.plotly_chart(fig_count_area, use_container_width=True)
                            
                            # Show data table
                            with st.expander("📋 View Data Table"):
                                pivot_count = count_data.pivot(index=group_col, columns='Status', values='Count').fillna(0)
                                st.dataframe(pivot_count, use_container_width=True)
                            
                            # ========== Payment Rate by Status (with time filtering) ==========
                            st.markdown("---")
                            st.header("📊 Payment Rate by Status")
                            
                            # Time filter selection
                            time_filter_type_rate = st.radio(
                                "Select Time Filter",
                                ["Day", "Hour", "Minute"],
                                horizontal=True,
                                key="time_filter_rate"
                            )
                            
                            # Reload button - Streamlit will automatically rerun when widget values change
                            st.button("🔄 Reload Chart", key="reload_rate", help="Click to refresh the chart")
                            
                            # Group by selected time filter
                            if time_filter_type_rate == "Day":
                                # Group by calendar day
                                group_col_rate = 'Date'
                                x_label_rate = 'Date'
                                df_rate = df.copy()
                            elif time_filter_type_rate == "Hour":
                                # Group by full date + hour
                                df_rate = df.copy()
                                df_rate['DateHour'] = df_rate['ParsedDateTime'].dt.strftime('%Y-%m-%d %H:00')
                                group_col_rate = 'DateHour'
                                x_label_rate = 'Date-Hour'
                            else:
                                # Group by full date + hour:minute
                                df_rate = df.copy()
                                df_rate['DateMinute'] = df_rate['ParsedDateTime'].dt.strftime('%Y-%m-%d %H:%M')
                                group_col_rate = 'DateMinute'
                                x_label_rate = 'Date-Time (Minute)'
                            
                            # Calculate rate by status and time bucket
                            total_by_time = df_rate.groupby(group_col_rate).size().reset_index(name='Total')
                            status_by_time = df_rate.groupby([group_col_rate, 'Status']).size().reset_index(name='Count')
                            
                            # Merge to calculate percentage
                            rate_data = status_by_time.merge(total_by_time, on=group_col_rate)
                            rate_data['Rate (%)'] = (rate_data['Count'] / rate_data['Total'] * 100).round(2)
                            
                            # Create stacked bar chart for rates
                            fig_rate = px.bar(
                                rate_data,
                                x=group_col_rate,
                                y='Rate (%)',
                                color='Status',
                                title=f'Payment Rate by Status ({time_filter_type_rate}) - Stacked',
                                labels={group_col_rate: x_label_rate, 'Rate (%)': 'Rate (%)'},
                                barmode='stack',
                                text='Rate (%)'
                            )
                            # Format hovertemplate to show Status name correctly
                            hovertemplate_rate = f"{x_label_rate}: %{{x}}<br>Status: %{{fullData.name}}<br>Rate: %{{y}}%<extra></extra>"
                            
                            fig_rate.update_traces(
                                texttemplate='%{text:.1f}%',
                                textposition='inside',
                                hovertemplate=hovertemplate_rate
                            )
                            fig_rate.update_layout(
                                xaxis_title=x_label_rate,
                                yaxis_title='Rate (%)',
                                height=500,
                                showlegend=True,
                                yaxis=dict(range=[0, 100])
                            )
                            st.plotly_chart(fig_rate, use_container_width=True)
                            
                            # Create line chart for Payment Rate by Status
                            fig_rate_line = px.line(
                                rate_data,
                                x=group_col_rate,
                                y='Rate (%)',
                                color='Status',
                                title=f'Payment Rate by Status ({time_filter_type_rate}) - Line Chart',
                                labels={group_col_rate: x_label_rate, 'Rate (%)': 'Rate (%)'},
                                markers=True
                            )
                            hovertemplate_line_rate = f"{x_label_rate}: %{{x}}<br>Status: %{{fullData.name}}<br>Rate: %{{y}}%<extra></extra>"
                            
                            fig_rate_line.update_traces(
                                hovertemplate=hovertemplate_line_rate
                            )
                            fig_rate_line.update_layout(
                                xaxis_title=x_label_rate,
                                yaxis_title='Rate (%)',
                                height=500,
                                showlegend=True,
                                yaxis=dict(range=[0, 100])
                            )
                            st.plotly_chart(fig_rate_line, use_container_width=True)

                            # Create stacked area chart for Payment Rate by Status
                            fig_rate_area = px.area(
                                rate_data,
                                x=group_col_rate,
                                y='Rate (%)',
                                color='Status',
                                title=f'Payment Rate by Status ({time_filter_type_rate}) - Stacked Area',
                                labels={group_col_rate: x_label_rate, 'Rate (%)': 'Rate (%)'},
                            )
                            hovertemplate_area_rate = f"{x_label_rate}: %{{x}}<br>Status: %{{fullData.name}}<br>Rate: %{{y}}%<extra></extra>"
                            
                            fig_rate_area.update_traces(
                                hovertemplate=hovertemplate_area_rate,
                                mode='lines',
                            )
                            fig_rate_area.update_layout(
                                xaxis_title=x_label_rate,
                                yaxis_title='Rate (%)',
                                height=500,
                                showlegend=True,
                                yaxis=dict(range=[0, 100]),
                            )
                            st.plotly_chart(fig_rate_area, use_container_width=True)
                            
                            # Show data table
                            with st.expander("📋 View Data Table"):
                                pivot_rate = rate_data.pivot(index=group_col_rate, columns='Status', values='Rate (%)').fillna(0)
                                st.dataframe(pivot_rate, use_container_width=True)
                            
                            # ========== Success Rate Analysis ==========
                            st.markdown("---")
                            st.header("✅ Success Rate Analysis")
                            
                            # Time filter selection for Success Rate
                            time_filter_type_sr = st.radio(
                                "Select Time Filter",
                                ["Day", "Hour", "Minute"],
                                horizontal=True,
                                key="time_filter_sr"
                            )
                            
                            # Reload button
                            st.button("🔄 Reload Chart", key="reload_sr", help="Click to refresh the chart")
                            
                            # Group by selected time filter
                            if time_filter_type_sr == "Day":
                                df_sr = df.copy()
                                df_sr['DateStr'] = df_sr['ParsedDateTime'].dt.strftime('%Y-%m-%d')
                                group_col_sr = 'DateStr'
                                x_label_sr = 'Date'
                            elif time_filter_type_sr == "Hour":
                                df_sr = df.copy()
                                df_sr['DateHour'] = df_sr['ParsedDateTime'].dt.strftime('%Y-%m-%d %H:00')
                                group_col_sr = 'DateHour'
                                x_label_sr = 'Date-Hour'
                            else:
                                df_sr = df.copy()
                                df_sr['DateMinute'] = df_sr['ParsedDateTime'].dt.strftime('%Y-%m-%d %H:%M')
                                group_col_sr = 'DateMinute'
                                x_label_sr = 'Date-Time (Minute)'
                            
                            # Calculate Success Rate
                            # SR Count = Approved + Settled
                            # SR Rate = (Approved + Settled) / (Approved + Settled + Rejected + Payment Expired)
                            
                            # Count by status and time
                            sr_status_counts = df_sr.groupby([group_col_sr, 'Status']).size().reset_index(name='Count')
                            
                            # Get all unique time buckets and sort them
                            time_buckets = sorted(df_sr[group_col_sr].unique())
                            
                            # Calculate SR Count and SR Rate for each time bucket
                            sr_data_list = []
                            for time_bucket in time_buckets:
                                time_data = sr_status_counts[sr_status_counts[group_col_sr] == time_bucket]
                                
                                # Get counts for each status (default to 0 if not found)
                                approved = int(time_data[time_data['Status'] == 'Approved']['Count'].sum()) if len(time_data[time_data['Status'] == 'Approved']) > 0 else 0
                                settled = int(time_data[time_data['Status'] == 'Settled']['Count'].sum()) if len(time_data[time_data['Status'] == 'Settled']) > 0 else 0
                                rejected = int(time_data[time_data['Status'] == 'Rejected']['Count'].sum()) if len(time_data[time_data['Status'] == 'Rejected']) > 0 else 0
                                payment_expired = int(time_data[time_data['Status'] == 'Payment Expired']['Count'].sum()) if len(time_data[time_data['Status'] == 'Payment Expired']) > 0 else 0
                                
                                # Calculate SR Count
                                sr_count = approved + settled
                                
                                # Calculate SR Rate
                                denominator = approved + settled + rejected + payment_expired
                                if denominator > 0:
                                    sr_rate = round((sr_count / denominator * 100), 2)
                                else:
                                    sr_rate = 0.0
                                
                                sr_data_list.append({
                                    group_col_sr: time_bucket,
                                    'SR Count': sr_count,
                                    'SR Rate (%)': sr_rate
                                })
                            
                            sr_data = pd.DataFrame(sr_data_list)
                            # Ensure proper sorting
                            sr_data = sr_data.sort_values(group_col_sr)
                            
                            # Debug: Show calculation details
                            with st.expander("🔍 Debug: SR Calculation Details", expanded=False):
                                st.write("**Status counts by time bucket:**")
                                st.dataframe(sr_status_counts, use_container_width=True)
                                st.write("**Calculated SR data:**")
                                st.dataframe(sr_data, use_container_width=True)
                            
                            # 1. Success Rate Count - Line Chart
                            st.subheader("📊 Success Rate Count")
                            fig_sr_count_line = px.line(
                                sr_data,
                                x=group_col_sr,
                                y='SR Count',
                                title=f'Success Rate Count ({time_filter_type_sr}) - Line Chart',
                                labels={group_col_sr: x_label_sr, 'SR Count': 'Success Rate Count (Approved + Settled)'},
                                markers=True,
                                color_discrete_sequence=['#2E86AB']  # Blue color for Count
                            )
                            hovertemplate_sr_count_line = f"{x_label_sr}: %{{x}}<br>SR Count: %{{y}}<extra></extra>"
                            fig_sr_count_line.update_traces(
                                hovertemplate=hovertemplate_sr_count_line,
                                line_color='#2E86AB',
                                marker_color='#2E86AB'
                            )
                            fig_sr_count_line.update_layout(
                                xaxis_title=x_label_sr,
                                yaxis_title='Success Rate Count',
                                height=400,
                                showlegend=False
                            )
                            st.plotly_chart(fig_sr_count_line, use_container_width=True)
                            
                            # 2. Success Rate Count - Stacked Area Chart
                            fig_sr_count_area = px.area(
                                sr_data,
                                x=group_col_sr,
                                y='SR Count',
                                title=f'Success Rate Count ({time_filter_type_sr}) - Stacked Area',
                                labels={group_col_sr: x_label_sr, 'SR Count': 'Success Rate Count (Approved + Settled)'},
                                color_discrete_sequence=['#2E86AB']  # Blue color for Count
                            )
                            hovertemplate_sr_count_area = f"{x_label_sr}: %{{x}}<br>SR Count: %{{y}}<extra></extra>"
                            fig_sr_count_area.update_traces(
                                hovertemplate=hovertemplate_sr_count_area,
                                mode='lines',
                                fillcolor='rgba(46, 134, 171, 0.6)',  # Blue with transparency
                                line_color='#2E86AB'
                            )
                            fig_sr_count_area.update_layout(
                                xaxis_title=x_label_sr,
                                yaxis_title='Success Rate Count',
                                height=400,
                                showlegend=False
                            )
                            st.plotly_chart(fig_sr_count_area, use_container_width=True)
                            
                            # 3. Success Rate Count - Bar Chart
                            fig_sr_count_bar = px.bar(
                                sr_data,
                                x=group_col_sr,
                                y='SR Count',
                                title=f'Success Rate Count ({time_filter_type_sr}) - Bar Chart',
                                labels={group_col_sr: x_label_sr, 'SR Count': 'Success Rate Count (Approved + Settled)'},
                                text='SR Count',
                                color_discrete_sequence=['#f54290']  # Blue color for Count
                            )
                            hovertemplate_sr_count_bar = f"{x_label_sr}: %{{x}}<br>SR Count: %{{y}}<extra></extra>"
                            fig_sr_count_bar.update_traces(
                                textposition='outside',
                                hovertemplate=hovertemplate_sr_count_bar,
                                marker_color='#2E86AB'
                            )
                            fig_sr_count_bar.update_layout(
                                xaxis_title=x_label_sr,
                                yaxis_title='Success Rate Count',
                                height=400,
                                showlegend=False
                            )
                            st.plotly_chart(fig_sr_count_bar, use_container_width=True)
                            
                            # 4. Success Rate Percentage - Line Chart
                            st.subheader("📈 Success Rate Percentage")
                            fig_sr_rate_line = px.line(
                                sr_data,
                                x=group_col_sr,
                                y='SR Rate (%)',
                                title=f'Success Rate Percentage ({time_filter_type_sr}) - Line Chart',
                                labels={group_col_sr: x_label_sr, 'SR Rate (%)': 'Success Rate (%)'},
                                markers=True,
                                color_discrete_sequence=['#F77F00']  # Orange color for Rate
                            )
                            hovertemplate_sr_rate_line = f"{x_label_sr}: %{{x}}<br>SR Rate: %{{y}}%<extra></extra>"
                            fig_sr_rate_line.update_traces(
                                hovertemplate=hovertemplate_sr_rate_line,
                                line_color='#F77F00',
                                marker_color='#F77F00'
                            )
                            fig_sr_rate_line.update_layout(
                                xaxis_title=x_label_sr,
                                yaxis_title='Success Rate (%)',
                                height=400,
                                showlegend=False,
                                yaxis=dict(range=[0, 100])
                            )
                            st.plotly_chart(fig_sr_rate_line, use_container_width=True)
                            
                            # 5. Success Rate Percentage - Stacked Area Chart
                            fig_sr_rate_area = px.area(
                                sr_data,
                                x=group_col_sr,
                                y='SR Rate (%)',
                                title=f'Success Rate Percentage ({time_filter_type_sr}) - Stacked Area',
                                labels={group_col_sr: x_label_sr, 'SR Rate (%)': 'Success Rate (%)'},
                                color_discrete_sequence=['#F77F00']  # Orange color for Rate
                            )
                            hovertemplate_sr_rate_area = f"{x_label_sr}: %{{x}}<br>SR Rate: %{{y}}%<extra></extra>"
                            fig_sr_rate_area.update_traces(
                                hovertemplate=hovertemplate_sr_rate_area,
                                mode='lines',
                                fillcolor='rgba(247, 127, 0, 0.6)',  # Orange with transparency
                                line_color='#F77F00'
                            )
                            fig_sr_rate_area.update_layout(
                                xaxis_title=x_label_sr,
                                yaxis_title='Success Rate (%)',
                                height=400,
                                showlegend=False,
                                yaxis=dict(range=[0, 100])
                            )
                            st.plotly_chart(fig_sr_rate_area, use_container_width=True)
                            
                            # 6. Success Rate Percentage - Bar Chart
                            fig_sr_rate_bar = px.bar(
                                sr_data,
                                x=group_col_sr,
                                y='SR Rate (%)',
                                title=f'Success Rate Percentage ({time_filter_type_sr}) - Bar Chart',
                                labels={group_col_sr: x_label_sr, 'SR Rate (%)': 'Success Rate (%)'},
                                text='SR Rate (%)',
                                color_discrete_sequence=['#F77F00']  # Orange color for Rate
                            )
                            hovertemplate_sr_rate_bar = f"{x_label_sr}: %{{x}}<br>SR Rate: %{{y}}%<extra></extra>"
                            fig_sr_rate_bar.update_traces(
                                texttemplate='%{text:.1f}%',
                                textposition='outside',
                                hovertemplate=hovertemplate_sr_rate_bar,
                                marker_color='#F77F00'
                            )
                            fig_sr_rate_bar.update_layout(
                                xaxis_title=x_label_sr,
                                yaxis_title='Success Rate (%)',
                                height=400,
                                showlegend=False,
                                yaxis=dict(range=[0, 100])
                            )
                            st.plotly_chart(fig_sr_rate_bar, use_container_width=True)
                            
                            # Show data table
                            with st.expander("📋 View Success Rate Data Table"):
                                st.dataframe(sr_data, use_container_width=True)
                        else:
                            st.warning("⚠️ Status column not found. Cannot generate status-based charts.")
                    else:
                        st.warning("⚠️ No valid datetime data found after parsing")
                else:
                    st.warning("⚠️ Could not find Date/Time column in the data")
                    st.info("Available columns: " + ", ".join(df.columns.tolist()))
                
                # Show raw data preview
                with st.expander("📋 View Raw Data (First 100 rows)"):
                    st.dataframe(df.head(100), use_container_width=True)
                
            else:
                st.warning("⚠️ Could not parse data from response")
        
        # Show raw response in expander
        with st.expander("📄 View Raw Response"):
            st.code(response_text[:5000] + "..." if len(response_text) > 5000 else response_text, language='html')


if __name__ == "__main__":
    render_analysist()

