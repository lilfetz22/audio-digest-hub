
import React from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Plus } from 'lucide-react';

interface AddSourceFormProps {
  newSource: { sender_email: string; custom_name: string };
  setNewSource: React.Dispatch<React.SetStateAction<{ sender_email: string; custom_name: string }>>;
  onSubmit: (e: React.FormEvent) => void;
}

export const AddSourceForm: React.FC<AddSourceFormProps> = ({
  newSource,
  setNewSource,
  onSubmit,
}) => {
  return (
    <form onSubmit={onSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div>
        <Label htmlFor="sender_email">Sender Email</Label>
        <Input
          id="sender_email"
          type="email"
          value={newSource.sender_email}
          onChange={(e) => setNewSource(prev => ({ ...prev, sender_email: e.target.value }))}
          placeholder="newsletter@example.com"
          required
        />
      </div>
      <div>
        <Label htmlFor="custom_name">Custom Name</Label>
        <Input
          id="custom_name"
          value={newSource.custom_name}
          onChange={(e) => setNewSource(prev => ({ ...prev, custom_name: e.target.value }))}
          placeholder="My Newsletter"
          required
        />
      </div>
      <div className="flex items-end">
        <Button type="submit" className="w-full">
          <Plus className="h-4 w-4 mr-2" />
          Add Source
        </Button>
      </div>
    </form>
  );
};
