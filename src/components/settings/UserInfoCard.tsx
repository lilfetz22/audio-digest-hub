
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { User } from '@supabase/supabase-js';

interface UserInfoCardProps {
  user: User | null;
}

export const UserInfoCard: React.FC<UserInfoCardProps> = ({ user }) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>User Information</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-gray-600">Email: {user?.email}</p>
      </CardContent>
    </Card>
  );
};
