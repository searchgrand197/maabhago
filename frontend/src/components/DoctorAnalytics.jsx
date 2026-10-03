import React, { useState, useEffect } from 'react';
import api from '../api';
import toast from 'react-hot-toast';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  PieChart, Pie, Cell, Legend
} from 'recharts';
import { TrendingUp, Users, DollarSign, Activity } from 'lucide-react';

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444']; // emerald, blue, amber, red

export default function DoctorAnalytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  async function fetchAnalytics() {
    try {
      setLoading(true);
      const res = await api.get('/doctor-analytics/');
      setData(res.data?.data || res.data);
    } catch (err) {
      toast.error('Failed to load financial analytics');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-gray-400">
        <Activity className="animate-spin mb-4" size={32} />
        <p>Crunching the numbers...</p>
      </div>
    );
  }

  if (!data) return null;

  const pieData = [
    { name: 'OPD Revenue', value: data.opd_revenue || 0 },
    { name: 'IPD Revenue', value: data.ipd_revenue || 0 },
  ].filter(d => d.value > 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-800">Financial Analytics</h2>
          <p className="text-sm font-semibold text-gray-400 mt-0.5">Last 30 Days Overview</p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gradient-to-r from-emerald-500 to-teal-500 rounded-2xl p-5 text-white shadow-md">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-emerald-100 text-sm font-semibold mb-1">Total Revenue</p>
              <h3 className="text-3xl font-black">₹{data.total_revenue?.toLocaleString() || 0}</h3>
            </div>
            <div className="p-2 bg-white/20 rounded-xl"><DollarSign size={24} /></div>
          </div>
        </div>
        
        <div className="bg-gradient-to-r from-blue-500 to-indigo-500 rounded-2xl p-5 text-white shadow-md">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-blue-100 text-sm font-semibold mb-1">Patients Seen</p>
              <h3 className="text-3xl font-black">{data.total_patients?.toLocaleString() || 0}</h3>
            </div>
            <div className="p-2 bg-white/20 rounded-xl"><Users size={24} /></div>
          </div>
        </div>

        <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm flex flex-col justify-center">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-gray-400 text-sm font-semibold mb-1">Revenue per Patient</p>
              <h3 className="text-2xl font-bold text-gray-800">
                ₹{data.total_patients > 0 ? Math.round(data.total_revenue / data.total_patients).toLocaleString() : 0}
              </h3>
            </div>
            <div className="p-2 bg-gray-50 rounded-xl text-gray-400"><TrendingUp size={24} /></div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Chart */}
        <div className="lg:col-span-2 bg-white rounded-2xl p-5 border border-gray-100 shadow-sm">
          <h3 className="font-bold text-gray-800 mb-6">Revenue & Patient Trends</h3>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.chart_data || []}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                <XAxis 
                  dataKey="date" 
                  tickFormatter={(val) => val.slice(5)} // Show MM-DD
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fill: '#9CA3AF', fontSize: 12}}
                  dy={10}
                />
                <YAxis 
                  yAxisId="left" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fill: '#9CA3AF', fontSize: 12}}
                  tickFormatter={(val) => '₹' + (val / 1000) + 'k'} // Show in 'k'
                  dx={-10}
                />
                <YAxis 
                  yAxisId="right" 
                  orientation="right" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fill: '#9CA3AF', fontSize: 12}}
                />
                <Tooltip 
                  contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  labelStyle={{ fontWeight: 'bold', color: '#374151', marginBottom: '4px' }}
                />
                <Legend iconType="circle" wrapperStyle={{ paddingTop: '20px' }}/>
                <Line yAxisId="left" type="monotone" dataKey="revenue" name="Revenue (₹)" stroke="#10b981" strokeWidth={3} dot={{r:0}} activeDot={{r:6}} />
                <Line yAxisId="right" type="monotone" dataKey="patients" name="Patients" stroke="#3b82f6" strokeWidth={3} dot={{r:0}} activeDot={{r:6}} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Breakdown Chart */}
        <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm">
          <h3 className="font-bold text-gray-800 mb-4">Revenue Breakdown</h3>
          {pieData.length === 0 ? (
            <div className="flex h-48 items-center justify-center text-gray-400 text-sm">
              No revenue data
            </div>
          ) : (
            <div className="h-64 mt-4 w-full flex-col flex items-center">
              <ResponsiveContainer width="100%" height="80%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => `₹${value.toLocaleString()}`} />
                </PieChart>
              </ResponsiveContainer>
              
              <div className="w-full flex justify-center gap-4 mt-2">
                {pieData.map((entry, idx) => (
                  <div key={entry.name} className="flex items-center gap-1.5 text-xs font-semibold text-gray-600">
                    <span className="w-3 h-3 rounded-full" style={{backgroundColor: COLORS[idx % COLORS.length]}}/>
                    {entry.name}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
